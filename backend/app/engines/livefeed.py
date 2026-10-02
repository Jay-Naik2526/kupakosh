"""Live rig feed hub: data posted by a rig system (WITSML / WITS0) -> anomaly + look-ahead -> every viewer of that well.

The replay (api/ws.py) plays recorded data from the database. This hub takes data from OUTSIDE while it is being
drilled: Oil India's eRTMAC, or any WITSML 1.4 / WITS0 sender, posts batches to /api/live/{well_id}/witsml (or
/wits0); viewers subscribe on /ws/live/{well_id}. Each batch goes through the same anomaly detector and look-ahead
as the replay, so an alert on a live well means exactly what it means in the replay and in the Hindsight test.

Honesty:
  * The source of every feed is shown to viewers (`source`, set by the sender or by the demo feeder).
  * The demo feeder (start_demo) re-sends RECORDED Utah FORGE data as WITSML documents through the real parser.
    It is labelled as such: it proves the connection path, not a live rig.
  * A feed with no data for livefeed.stale_s is reported as stale, never as "all clear".
State is in memory (one process); a restart clears it, and senders simply keep posting.
"""
from __future__ import annotations

import asyncio
import os
import secrets
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from starlette.concurrency import run_in_threadpool

from app.config import DATA_DIR, cfg
from app.engines.anomaly import AnomalyDetector

DEMO_SOURCE = "Demo feeder: recorded Utah FORGE rig-sensor data (CC-BY 4.0) re-sent as WITSML 1.4.1 documents — not a live rig"


def feed_token() -> str:
    """Senders must present this token. KK_FEED_TOKEN wins; otherwise a random token is created once and kept in
    data/processed/feed_token.txt (readable only on the server), so no default password ever ships."""
    env = os.environ.get("KK_FEED_TOKEN")
    if env:
        return env
    p = DATA_DIR / "processed" / "feed_token.txt"
    if p.exists():
        return p.read_text().strip()
    p.parent.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_urlsafe(24)
    p.write_text(tok)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return tok


class Feed:
    def __init__(self, well_id: int, name: str, source: str):
        c = cfg()
        self.well_id, self.name, self.source = well_id, name, source
        self.started = datetime.now(timezone.utc)
        self.last_rx: float | None = None
        self.last_rx_wall: datetime | None = None
        self.samples: deque = deque(maxlen=c["livefeed"]["keep_samples"])
        self.det: AnomalyDetector | None = None
        self.la: dict | None = None
        self.last_md_assessed: float | None = None
        self.last_alert: dict[tuple, datetime] = {}
        self.subs: set[asyncio.Queue] = set()
        self.last_sub_seen = time.monotonic()
        self.n_rx = self.n_posts = 0
        self.channels: set[str] = set()
        self.skipped: set[str] = set()
        self.lock = asyncio.Lock()
        self.demo = source == DEMO_SOURCE

    def info(self) -> dict:
        stale_s = cfg()["livefeed"]["stale_s"]
        age = None if self.last_rx is None else round(time.monotonic() - self.last_rx, 1)
        last = self.samples[-1] if self.samples else None
        return {"well_id": self.well_id, "well": self.name, "source": self.source, "demo": self.demo,
                "started": self.started.isoformat(), "last_data": self.last_rx_wall.isoformat() if self.last_rx_wall else None,
                "seconds_since_data": age, "stale": age is None or age > stale_s, "samples": self.n_rx, "posts": self.n_posts,
                "channels": sorted(self.channels), "ignored": sorted(self.skipped), "viewers": len(self.subs),
                "bit_md_m": last.get("md_m") if last else None}


FEEDS: dict[int, Feed] = {}
_DEMO: dict = {}


def get_feed(well_id: int) -> Feed | None:
    return FEEDS.get(well_id)


def _open(well_id: int, name: str, source: str) -> Feed:
    f = FEEDS.get(well_id)
    if f and f.source == source:
        return f
    if f is None and len(FEEDS) >= cfg()["livefeed"]["max_feeds"]:
        stale = [w for w, x in FEEDS.items() if x.info()["stale"] and not x.subs]
        if not stale:
            raise OverflowError("too many live feeds at once")
        FEEDS.pop(stale[0])
    new = Feed(well_id, name, source)
    if f:  # a new sender for the same well: keep the viewers, start the series afresh
        new.subs = f.subs
    FEEDS[well_id] = new
    return new


async def push(well_id: int, name: str, parsed: dict, source: str) -> dict:
    """Add one posted batch and broadcast it. Returns what was accepted (sent back to the sender)."""
    from app.db.session import SessionLocal
    from app.engines.lookahead import assess
    f = _open(well_id, name, source)
    attach_waiting(well_id)
    rows = parsed["samples"]
    now = datetime.now(timezone.utc)
    async with f.lock:
        f.n_posts += 1
        f.channels |= set(parsed["channels"])
        f.skipped |= set(parsed["skipped"])
        if not rows:
            return {"accepted": 0, **_ack(f)}
        if f.det is None:
            ts = [datetime.fromisoformat(r["t"]) for r in rows[:50] if r.get("t")]
            period = (ts[-1] - ts[0]).total_seconds() / (len(ts) - 1) if len(ts) > 1 else 5.0
            f.det = AnomalyDetector(max(period, 0.5))
        anomaly = None
        batch = []
        for r in rows:
            s = {k: r.get(k) for k in ("md_m", "bit_md_m", "rop", "wob", "rpm", "torque", "spp", "flow_in", "pit_vol", "hookload")}
            s["t"] = r.get("t") or now.isoformat()
            s["mw_ppg"] = None  # mud weight is not a WITSML log curve here; the mud-check reports carry it
            a = f.det.update(s)
            if a:
                anomaly = a
            batch.append(s)
            f.samples.append(s)
        f.n_rx += len(batch)
        f.last_rx, f.last_rx_wall = time.monotonic(), now
        step = max(1, len(batch) // 20)
        out = batch[::step]
        if out[-1] is not batch[-1]:
            out.append(batch[-1])
        msg = {"type": "samples", "t": batch[-1]["t"], "samples": out, "anomaly": anomaly, "feed": f.info()}
        md = next((s["md_m"] for s in reversed(batch) if s.get("md_m") is not None), None)
        if md is not None and (f.last_md_assessed is None or abs(md - f.last_md_assessed) >= 1.0 or anomaly):
            def run():
                with SessionLocal() as db:
                    return assess(db, well_id, md, anomaly)
            la = await run_in_threadpool(run)
            f.last_md_assessed = md
            cooldown = cfg()["lookahead"]["cooldown_s"]
            t_now = datetime.fromisoformat(batch[-1]["t"])
            fresh = []
            for a in la["alerts"] + la["notices"]:
                k = (a["hazard"], a["formation"], a["level"])
                prev = f.last_alert.get(k)
                if prev is None or (t_now - prev).total_seconds() >= cooldown:
                    f.last_alert[k] = t_now
                    fresh.append(k)
            f.la = {**la, "new_keys": [list(k) for k in fresh]}
            msg["lookahead"] = f.la
        for q in list(f.subs):
            if q.qsize() < 200:  # a slow viewer drops frames rather than holding up the feed
                q.put_nowait(msg)
    return {"accepted": len(batch), **_ack(f)}


def _ack(f: Feed) -> dict:
    i = f.info()
    return {k: i[k] for k in ("well", "samples", "channels", "ignored", "viewers", "bit_md_m")}


def subscribe(well_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    f = FEEDS.get(well_id)
    if f is not None:
        f.subs.add(q)
        f.last_sub_seen = time.monotonic()
    else:
        _WAITING.setdefault(well_id, set()).add(q)
    return q


_WAITING: dict[int, set[asyncio.Queue]] = {}


def attach_waiting(well_id: int) -> None:
    """Viewers who opened the live view before the first data arrived."""
    f = FEEDS.get(well_id)
    if f and well_id in _WAITING:
        f.subs |= _WAITING.pop(well_id)


def unsubscribe(well_id: int, q: asyncio.Queue) -> None:
    f = FEEDS.get(well_id)
    if f:
        f.subs.discard(q)
        f.last_sub_seen = time.monotonic()
    _WAITING.get(well_id, set()).discard(q)


def snapshot(well_id: int) -> dict | None:
    """What a viewer joining late needs: the recent samples and the latest look-ahead."""
    f = FEEDS.get(well_id)
    if not f:
        return None
    return {"type": "snapshot", "samples": list(f.samples)[-1500:], "lookahead": f.la, "feed": f.info()}


# ---------------------------------------------------------------- demo feeder -------------------------------------------------

def demo_info() -> dict | None:
    d = _DEMO.get("state")
    return dict(d) if d else None


async def start_demo(well_id: int, speed: float, start_md: float | None) -> dict:
    """Re-send a recorded well as WITSML documents through the real parser and hub. One demo at a time."""
    from sqlalchemy import select

    from app.db.models import RealtimeSample, Well
    from app.db.session import SessionLocal
    from app.ingest.witsml_stream import parse_witsml_log, to_witsml_log

    def load():
        with SessionLocal() as db:
            w = db.get(Well, well_id)
            rows = db.execute(select(RealtimeSample).where(RealtimeSample.well_id == well_id).order_by(RealtimeSample.t)).scalars().all()
            out = [{"t": r.t if r.t.tzinfo else r.t.replace(tzinfo=timezone.utc), **{k: getattr(r, k) for k in
                    ("md_m", "bit_md_m", "rop", "wob", "rpm", "torque", "spp", "flow_in", "pit_vol", "hookload")}} for r in rows]
            return (w.canonical_name if w else None), out
    name, rows = await run_in_threadpool(load)
    if not name:
        raise KeyError("well not found")
    if not rows:
        raise LookupError("no recorded sensor data for this well to re-send")
    await stop_demo()
    c = cfg()["livefeed"]
    speed = min(max(speed, 1.0), cfg()["replay"]["max_speed"])
    i = next((k for k, r in enumerate(rows) if (r["md_m"] or 0) >= start_md), 0) if start_md is not None else 0
    if well_id in FEEDS and FEEDS[well_id].demo:  # a fresh demo starts a fresh series; viewers stay attached
        old = FEEDS.pop(well_id)
        _WAITING.setdefault(well_id, set()).update(old.subs)
    state = {"well_id": well_id, "well": name, "speed": speed, "start_md": start_md, "started": datetime.now(timezone.utc).isoformat(),
             "documents_sent": 0, "rows_sent": 0, "bytes_sent": 0, "source": DEMO_SOURCE, "running": True}
    _DEMO["state"] = state

    async def loop(i: int):
        t0 = time.monotonic()
        sim_t = rows[i]["t"]
        try:
            while i < len(rows) and time.monotonic() - t0 < c["demo_max_s"]:
                f = FEEDS.get(well_id)
                if f and not f.subs and time.monotonic() - f.last_sub_seen > c["demo_idle_s"]:
                    break  # nobody watching
                sim_t += timedelta(seconds=speed * c["demo_tick_s"])
                chunk = []
                while i < len(rows) and rows[i]["t"] <= sim_t:
                    chunk.append(rows[i])
                    i += 1
                if chunk:
                    doc = to_witsml_log(name, chunk)  # what a WITSML server would send …
                    parsed = parse_witsml_log(doc)    # … read back by the same parser a real sender's post goes through
                    await push(well_id, name, parsed, DEMO_SOURCE)
                    state["documents_sent"] += 1
                    state["rows_sent"] += len(chunk)
                    state["bytes_sent"] += len(doc)
                await asyncio.sleep(c["demo_tick_s"])
        finally:
            state["running"] = False
            f = FEEDS.get(well_id)
            if f and f.demo:
                for q in list(f.subs):
                    q.put_nowait({"type": "end", "feed": f.info()})

    _DEMO["task"] = asyncio.create_task(loop(i))
    return state


async def stop_demo() -> None:
    t = _DEMO.pop("task", None)
    if t and not t.done():
        t.cancel()
        try:
            await t
        except (asyncio.CancelledError, Exception):  # noqa: BLE001 - stopping must never fail
            pass
    if _DEMO.get("state"):
        _DEMO["state"]["running"] = False
