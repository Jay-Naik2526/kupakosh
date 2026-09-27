"""Read-mostly in-memory context shared by the engines (wells, tops, documented wells, events).

Built once per process from the DB; call `reset()` after a rebuild.
"""
from __future__ import annotations

import math
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import select

from app.db.models import Document, Event, Well
from app.db.session import SessionLocal
from app.engines.formations import TopIndex


@dataclass
class Ctx:
    wells: dict[int, Well]
    tops: TopIndex
    documented: set[int]                       # wells with at least one report (history or DDR)
    events: dict[int, list[Event]]             # well_id -> trusted events (not needs_review)
    ev_wf: dict[tuple[int, str, str], list[Event]] = field(default_factory=dict)  # (well, formation, hazard)
    penetrated: dict[str, set[int]] = field(default_factory=dict)  # formation -> documented wells that penetrated it


_LOCK = threading.Lock()


def ctx() -> Ctx:
    """Built once per process; concurrent first requests wait for the single build instead of each building
    (a cold server hit by many requests at once would otherwise exhaust the DB connection pool)."""
    c = _build.cache_info()
    if c.currsize:
        return _build()
    with _LOCK:
        return _build()


@lru_cache(maxsize=1)
def _build() -> Ctx:
    with SessionLocal() as db:
        wells = {w.id: w for w in db.scalars(select(Well))}
        tops = TopIndex(db)
        documented = {d for (d,) in db.execute(select(Document.well_id).distinct()) if d is not None}
        events: dict[int, list[Event]] = defaultdict(list)
        ev_wf: dict[tuple[int, str, str], list[Event]] = defaultdict(list)
        for e in db.scalars(select(Event).where(Event.needs_review.is_(False))):
            events[e.well_id].append(e)
            if e.formation:
                ev_wf[(e.well_id, e.formation, e.hazard)].append(e)
        pen: dict[str, set[int]] = defaultdict(set)
        for wid in documented:
            for f in tops.penetrated(wid):
                pen[f].add(wid)
        db.expunge_all()
    return Ctx(wells=wells, tops=tops, documented=documented, events=events, ev_wf=dict(ev_wf), penetrated=dict(pen))


def reset():
    _build.cache_clear()


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
