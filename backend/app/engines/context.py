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
    ev_wf_records: dict[tuple[int, str, str], list[Event]] = field(default_factory=dict)  # written records only (no engineer feedback)
    n_feedback: int = 0                        # engineer "problem" verdicts merged into ev_wf


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
        records = {k: list(v) for k, v in ev_wf.items()}
        # engineer feedback (self-correcting alerts): a "problem" verdict is a human-labelled record for that
        # (well, layer, hazard). It feeds base rates and posteriors (ev_wf); the Hindsight test scores on records only.
        n_fb = 0
        from sqlalchemy import inspect
        from app.db.models import AlertFeedback
        if inspect(db.bind).has_table(AlertFeedback.__tablename__):  # absent on a database built before this feature
            for f in db.scalars(select(AlertFeedback).where(AlertFeedback.verdict == "problem")):
                ev_wf[(f.well_id, f.formation, f.hazard)].append(Event(
                    id=-f.id, well_id=f.well_id, hazard=f.hazard, md_m=f.md_m, formation=f.formation, confidence=1.0, method="human",
                    needs_review=False, evidence_span=f"Engineer verdict: problem happened. {f.note or ''}".strip(),
                    source_ref=f"feedback:{f.id} ({f.reviewer})"))
                n_fb += 1
        pen: dict[str, set[int]] = defaultdict(set)
        for wid in documented:
            for f in tops.penetrated(wid):
                pen[f].add(wid)
        db.expunge_all()
    return Ctx(wells=wells, tops=tops, documented=documented, events=events, ev_wf=dict(ev_wf), penetrated=dict(pen),
               ev_wf_records=records, n_feedback=n_fb)


def reset():
    _build.cache_clear()


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
