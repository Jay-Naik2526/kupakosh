"""WS /ws/replay/{well_id}?speed=&start_md=  — replay of real recorded rig-sensor data (labelled REPLAY)."""
from __future__ import annotations

import asyncio
from bisect import bisect_right
from datetime import timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import cfg
from app.db.models import MudCheck, RealtimeSample, Well
from app.db.session import SessionLocal
from app.engines.anomaly import AnomalyDetector
from app.engines.lookahead import assess

router = APIRouter()
FIELDS = ("md_m", "bit_md_m", "rop", "wob", "rpm", "torque", "spp", "flow_in", "pit_vol", "hookload")


@router.websocket("/ws/replay/{well_id}")
async def replay(ws: WebSocket, well_id: int, speed: float | None = None, start_md: float | None = None):
    await ws.accept()
    c = cfg()
    speed = min(speed or c["replay"]["default_speed"], c["replay"]["max_speed"])
    tick = c["replay"]["tick_ms"] / 1000
    cooldown = c["lookahead"]["cooldown_s"]
    with SessionLocal() as db:
        w = db.get(Well, well_id)
        rows = db.execute(select(RealtimeSample).where(RealtimeSample.well_id == well_id).order_by(RealtimeSample.t)).scalars().all()
        mud = [(m.measured, m.mw_ppg, m.source_ref) for m in db.scalars(select(MudCheck).where(MudCheck.well_id == well_id).order_by(MudCheck.measured)) if m.measured]
        db.expunge_all()
    if not rows:
        await ws.send_json({"type": "error", "message": "no recorded sensor data for this well"})
        await ws.close()
        return
    i = 0
    if start_md is not None:
        i = next((k for k, r in enumerate(rows) if (r.md_m or 0) >= start_md), 0)
    period = (rows[min(len(rows) - 1, 50)].t - rows[0].t).total_seconds() / max(1, min(len(rows) - 1, 50))
    det = AnomalyDetector(period)
    mud_dates = [m[0] for m in mud]
    await ws.send_json({"type": "hello", "mode": "REPLAY", "well": w.canonical_name, "well_id": w.id, "speed": speed,
                        "t0": rows[i].t.isoformat(), "t_end": rows[-1].t.isoformat(), "n": len(rows),
                        "source": "Utah FORGE Pason rig-sensor data (CC-BY 4.0), replayed — not live"})
    sim_t = rows[i].t
    last_alert: dict[tuple, object] = {}
    last_md_assessed = None
    try:
        while i < len(rows):
            sim_t = sim_t + timedelta(seconds=speed * tick)
            batch = []
            anomaly = None
            while i < len(rows) and rows[i].t <= sim_t:
                r = rows[i]
                s = {k: getattr(r, k) for k in FIELDS}
                a = det.update(s)
                if a:
                    anomaly = a
                j = bisect_right(mud_dates, r.t.date()) - 1
                s["mw_ppg"] = mud[j][1] if j >= 0 else None
                s["t"] = r.t.isoformat()
                batch.append(s)
                i += 1
            if not batch:
                await asyncio.sleep(tick)
                continue
            step = max(1, len(batch) // 20)
            out = batch[::step]
            if out[-1] is not batch[-1]:
                out.append(batch[-1])
            msg = {"type": "samples", "t": batch[-1]["t"], "samples": out, "anomaly": anomaly}
            md = batch[-1]["md_m"] or 0
            if last_md_assessed is None or abs(md - last_md_assessed) >= 1.0 or anomaly:
                with SessionLocal() as db:
                    la = assess(db, well_id, md, anomaly)
                last_md_assessed = md
                fresh = []
                for a in la["alerts"] + la["notices"]:
                    k = (a["hazard"], a["formation"], a["level"])
                    prev = last_alert.get(k)
                    if prev is None or (rows[i - 1].t - prev).total_seconds() >= cooldown:
                        last_alert[k] = rows[i - 1].t
                        fresh.append(k)
                msg["lookahead"] = {**la, "new_keys": [list(k) for k in fresh]}
            await ws.send_json(msg)
            await asyncio.sleep(tick)
        await ws.send_json({"type": "end"})
    except WebSocketDisconnect:
        return
