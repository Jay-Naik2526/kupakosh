"""Live rig feed (eRTMAC / any WITSML 1.4 or WITS0 sender) — see engines/livefeed.py.

  POST /api/live/{well_id}/witsml        body: WITSML 1.4.1 <logs> XML           header: Authorization: Bearer <token>
  POST /api/live/{well_id}/wits0?units=   body: WITS Level 0 records (&& … !!)   header: Authorization: Bearer <token>
  GET  /api/live                          feeds now streaming (no token needed: shows source, freshness, channels)
  POST /api/live/{well_id}/demo           start the demo feeder (recorded data re-sent as WITSML; labelled)
  POST /api/live/demo/stop
  WS   /ws/live/{well_id}                 viewers: same message shape as /ws/replay
"""
from __future__ import annotations

import asyncio
import hmac

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.db.models import Well
from app.db.session import SessionLocal
from app.engines import livefeed as lf
from app.ingest.witsml_stream import FeedError, parse_witsml_log, parse_wits0

router = APIRouter()


def _auth(req: Request) -> None:
    got = req.headers.get("authorization", "").removeprefix("Bearer ").strip() or req.headers.get("x-feed-token", "")
    if not got or not hmac.compare_digest(got, lf.feed_token()):
        raise HTTPException(401, "feed token missing or wrong (Authorization: Bearer <token>)")


def _well(well_id: int) -> str:
    with SessionLocal() as db:
        w = db.get(Well, well_id)
        if not w:
            raise HTTPException(404, "well not found — register the well (location + formation tops) before streaming to it")
        return w.canonical_name


def _source(req: Request, default: str) -> str:
    s = (req.headers.get("x-feed-source") or "").strip()[:160]
    return s or default


async def _ingest(well_id: int, parsed: dict, source: str) -> dict:
    try:
        return await lf.push(well_id, _well(well_id), parsed, source)
    except OverflowError as e:
        raise HTTPException(429, str(e)) from None


@router.post("/api/live/{well_id}/witsml")
async def post_witsml(well_id: int, req: Request):
    _auth(req)
    try:
        parsed = parse_witsml_log(await req.body())
    except FeedError as e:
        raise HTTPException(422, str(e)) from None
    return await _ingest(well_id, parsed, _source(req, "WITSML 1.4.1 sender (unnamed)"))


@router.post("/api/live/{well_id}/wits0")
async def post_wits0(well_id: int, req: Request, units: str = "metric"):
    _auth(req)
    try:
        parsed = parse_wits0((await req.body()).decode("ascii", "replace"), units)
    except FeedError as e:
        raise HTTPException(422, str(e)) from None
    return await _ingest(well_id, parsed, _source(req, f"WITS0 sender (unnamed, {units} units)"))


@router.get("/api/live")
def feeds():
    return {"feeds": [f.info() for f in lf.FEEDS.values()], "demo": lf.demo_info(),
            "formats": ["WITSML 1.4.1 log (POST /api/live/{well_id}/witsml)", "WITS Level 0 record 01 (POST /api/live/{well_id}/wits0?units=metric|imperial)"]}


class DemoBody(BaseModel):
    speed: float = 120
    start_md: float | None = None


@router.post("/api/live/{well_id}/demo")
async def demo(well_id: int, body: DemoBody):
    try:
        return await lf.start_demo(well_id, body.speed, body.start_md)
    except KeyError:
        raise HTTPException(404, "well not found") from None
    except LookupError as e:
        raise HTTPException(422, str(e)) from None


@router.post("/api/live/demo/stop")
async def demo_stop():
    await lf.stop_demo()
    return {"ok": True, "demo": lf.demo_info()}


@router.websocket("/ws/live/{well_id}")
async def live(ws: WebSocket, well_id: int):
    await ws.accept()
    q = lf.subscribe(well_id)
    try:
        snap = lf.snapshot(well_id)
        await ws.send_json({"type": "hello", "mode": "LIVE", "well_id": well_id, "feed": snap["feed"] if snap else None})
        if snap:
            await ws.send_json(snap)
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=10)
            except asyncio.TimeoutError:  # heartbeat: lets the page show "no data for N s" honestly
                f = lf.get_feed(well_id)
                await ws.send_json({"type": "heartbeat", "feed": f.info() if f else None})
                continue
            await ws.send_json(msg)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        lf.unsubscribe(well_id, q)
