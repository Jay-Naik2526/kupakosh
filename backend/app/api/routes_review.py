"""Human review queue for extracted events flagged `needs_review` (SPEC.md §9.1, §0.4/§0.5).

Every extracted fact must be traceable and, when confidence is low, checked by a person before it
feeds the ledger/hazard/wiki engines. This router lets a reviewer confirm, reject, or relabel an
`Event` row, keeps a plain audit trail (`data/processed/review_log.jsonl`), and asks the in-process
engine caches to drop anything they memoized so the change is visible immediately.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import DATA_DIR, taxonomy
from app.db.models import Event, Well
from app.db.session import get_db
from app.engines import caches
from app.engines.formations import pretty

router = APIRouter(prefix="/api/review")

REVIEW_LOG = DATA_DIR / "processed" / "review_log.jsonl"


def _event_snapshot(e: Event) -> dict:
    return {"id": e.id, "well_id": e.well_id, "hazard": e.hazard, "md_m": e.md_m, "formation": e.formation,
            "confidence": e.confidence, "method": e.method, "needs_review": e.needs_review,
            "evidence_span": e.evidence_span, "source_ref": e.source_ref}


def _log(event_id: int, decision: str, reviewer: str, note: str | None, before: dict, after: dict | None) -> None:
    """Append one JSON line to the review audit trail (kept alongside the DB, never inside it)."""
    REVIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {"time": datetime.now(timezone.utc).isoformat(), "event_id": event_id, "decision": decision,
           "reviewer": reviewer, "note": note, "before": before, "after": after}
    with REVIEW_LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")


@router.get("/events")
def review_events(hazard: str | None = None, country: str | None = None, limit: int = 50, offset: int = 0,
                   db: Session = Depends(get_db)):
    """Events needing human review. Country is filtered via a join on Well.country, never a well-id IN list."""
    base = select(Event, Well.canonical_name, Well.country).join(Well, Well.id == Event.well_id).where(Event.needs_review.is_(True))
    if hazard:
        base = base.where(Event.hazard == hazard)
    if country:
        base = base.where(Well.country == country)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(Event.well_id, Event.md_m).limit(limit).offset(offset)).all()
    events = [{"id": e.id, "well_id": e.well_id, "well": name, "country": cc, "hazard": e.hazard,
               "md_m": e.md_m, "formation": e.formation, "formation_label": pretty(e.formation),
               "confidence": e.confidence, "method": e.method, "evidence_span": e.evidence_span,
               "source_ref": e.source_ref} for e, name, cc in rows]
    return {"total": total, "limit": limit, "offset": offset, "events": events}


class ReviewDecision(BaseModel):
    decision: str  # confirm | reject | relabel
    hazard: str | None = None
    reviewer: str
    note: str | None = None


@router.post("/events/{event_id}")
def review_event(event_id: int, body: ReviewDecision, db: Session = Depends(get_db)):
    e = db.get(Event, event_id)
    if not e:
        raise HTTPException(404, "event not found")
    if body.decision not in ("confirm", "reject", "relabel"):
        raise HTTPException(422, "decision must be confirm | reject | relabel")
    if not body.reviewer or not body.reviewer.strip():
        raise HTTPException(422, "reviewer is required")

    before = _event_snapshot(e)

    if body.decision == "confirm":
        e.needs_review = False
        e.method = "human"
        db.commit()
        after = _event_snapshot(e)
    elif body.decision == "relabel":
        hazards = taxonomy()["hazards"]
        if not body.hazard or body.hazard not in hazards:
            raise HTTPException(422, f"hazard must be one of: {', '.join(hazards)}")
        e.hazard = body.hazard
        e.method = "human"
        db.commit()
        after = _event_snapshot(e)
    else:  # reject: no schema field to soft-delete against, so the flagged (unconfirmed) fact is removed
        db.delete(e)
        db.commit()
        after = None

    _log(event_id, body.decision, body.reviewer, body.note, before, after)
    caches.reset_all()
    return {"ok": True, "id": event_id, "decision": body.decision, "before": before, "after": after}
