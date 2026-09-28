"""Re-apply human review decisions after a rebuild.

A rebuild recreates every Event, so decisions made in the review queue (data/processed/review_log.jsonl) would be lost.
Each logged decision is matched to the new event by (source_ref, hazard before the decision) — the same report line and
the same extracted hazard — and applied again in log order. Decisions whose line no longer yields that event are counted
as "stale" and left alone (never guessed onto another event).
"""
from __future__ import annotations

import json

from sqlalchemy import select

from app.config import DATA_DIR
from app.db.models import Event

LOG = DATA_DIR / "processed" / "review_log.jsonl"


def run(db, log=print) -> dict:
    n = {"applied": 0, "stale": 0}
    if not LOG.exists():
        log("review replay: no review log")
        return n
    for line in LOG.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        b, a = r.get("before") or {}, r.get("after")
        ev = db.scalars(select(Event).where(Event.source_ref == b.get("source_ref"), Event.hazard == b.get("hazard"))).first()
        if ev is None:
            n["stale"] += 1
            continue
        if r["decision"] == "reject":
            db.delete(ev)
        else:
            ev.hazard = a.get("hazard", ev.hazard)
            ev.needs_review = a.get("needs_review", ev.needs_review)
            ev.method = a.get("method", "human")
            # an AI or human reviewer may add a depth quoted verbatim from the evidence (scripts/apply_ai_review.py)
            if "md_m" in a and a.get("method") == "ai_review":
                ev.md_m = a["md_m"]          # verified depth, or None when the reviewer could not verify one
                ev.formation = a.get("formation")
        n["applied"] += 1
    db.flush()
    log(f"review replay: {n}")
    return n
