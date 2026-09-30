"""Self-correcting alerts: an engineer marks an alert "problem happened" / "no problem" / "unsure".

A "problem" verdict is stored as a human-labelled record for that (well, layer, hazard) and merged into the
shared context (engines.context), so base rates and posteriors for OTHER wells learn from it straight away,
and the learned Hindsight ranker retrains on the next refresh. The Hindsight test itself keeps scoring on the
written records only, so feedback cannot raise the measured accuracy.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import taxonomy
from app.db.models import AlertFeedback, Well
from app.db.session import get_db

router = APIRouter(prefix="/api/feedback")


class FeedbackIn(BaseModel):
    well_id: int
    formation: str
    hazard: str
    verdict: Literal["problem", "no_problem", "unsure"]
    md_m: float | None = None
    note: str | None = Field(None, max_length=1000)
    reviewer: str = Field(..., min_length=2, max_length=80)
    role: str | None = Field(None, max_length=80)


def _field_rate(formation: str, hazard: str) -> dict:
    from app.engines import hazard as hz
    rate, n, scope = hz.base_rate(formation, hazard)
    return {"rate": round(rate, 4), "n_wells": n, "scope": scope}


@router.post("")
def add(body: FeedbackIn, db: Session = Depends(get_db)):
    if body.hazard not in taxonomy()["hazards"]:
        raise HTTPException(422, "unknown hazard")
    if db.get(Well, body.well_id) is None:
        raise HTTPException(404, "well not found")
    before = _field_rate(body.formation, body.hazard)
    row = AlertFeedback(**body.model_dump())
    db.add(row)
    db.commit()
    changed = body.verdict == "problem"
    if changed:  # the new label must reach every estimate: drop the caches that hold labels (not the search index)
        from app.engines import context, hazard, lookahead
        context.reset()
        hazard.base_rate.cache_clear()
        lookahead._profile.cache_clear()
    after = _field_rate(body.formation, body.hazard)
    return {"id": row.id, "verdict": row.verdict, "learned": changed, "field_rate_before": before, "field_rate_after": after,
            "note": ("Stored as a human-labelled record: estimates for other wells in this layer now include it; the learned "
                     "ranker retrains on the next Hindsight refresh. The Hindsight test still scores on written records only.")
            if changed else "Stored. Only 'problem happened' verdicts change the estimates; this one is kept for review."}


@router.get("")
def list_(well_id: int | None = None, limit: int = 50, db: Session = Depends(get_db)):
    q = select(AlertFeedback, Well.canonical_name).join(Well, Well.id == AlertFeedback.well_id).order_by(AlertFeedback.id.desc()).limit(limit)
    if well_id is not None:
        q = q.where(AlertFeedback.well_id == well_id)
    return [{"id": f.id, "well_id": f.well_id, "well": name, "formation": f.formation, "hazard": f.hazard, "verdict": f.verdict,
             "md_m": f.md_m, "note": f.note, "reviewer": f.reviewer, "role": f.role,
             "created_at": f.created_at.isoformat() if f.created_at else None} for f, name in db.execute(q).all()]


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(AlertFeedback.verdict, func.count()).group_by(AlertFeedback.verdict)).all())
    return {"total": sum(counts.values()), "by_verdict": counts}
