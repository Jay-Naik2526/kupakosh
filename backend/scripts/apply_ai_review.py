"""Apply an AI review pass to the event review queue (authorised by the project lead, 28 Sept 2026).

Input: one or more JSON files of decisions, each item
  {"id", "decision": confirm|relabel|reject, "hazard"?, "depth_quote"?, "depth_value"?, "depth_unit"?, "reason"}
produced by reviewers reading each event's verbatim evidence sentence (brief: docs/AI_REVIEW.md).

Every decision is validated before it touches the DB:
  * the event must still be in the queue (needs_review = true);
  * a relabel must name a taxonomy hazard;
  * a depth is kept only if `depth_quote` is a verbatim substring of the evidence, contains the number,
    and the converted depth lies within (0, TD * 1.05] of the well (when TD is known);
  * an auto-extracted depth on a confirmed event is cleared unless the reviewer verified it from the sentence.
Accepted decisions are written with method = "ai_review" and the reviewer name below, and appended to
data/processed/review_log.jsonl, so they survive rebuilds (engines/review_replay.py) and stay distinguishable
from human review everywhere (Accuracy page counts them separately).

Usage: python -m scripts.apply_ai_review decisions0.json decisions1.json ...
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

from app.api.routes_review import _event_snapshot, _log
from app.config import taxonomy
from app.db.models import Event
from app.db.session import SessionLocal
from app.engines import caches
from app.engines.context import ctx

REVIEWER = "AI review, authorised by Jay Naik"
FT = 0.3048


def _depth_m(item: dict, evidence: str, td: float | None) -> tuple[float | None, str | None]:
    q, v, u = item.get("depth_quote"), item.get("depth_value"), (item.get("depth_unit") or "").lower()
    if not q or v is None or u not in ("m", "ft"):
        return None, None
    if q not in (evidence or ""):
        return None, "depth quote not verbatim"
    digits = re.sub(r"[^\d.]", "", q.replace(",", ""))
    try:
        if abs(float(digits) - float(v)) > 0.5:
            return None, "depth value not in quote"
    except ValueError:
        return None, "depth quote has no number"
    md = float(v) * (FT if u == "ft" else 1.0)
    if md <= 0 or (td and md > td * 1.05):
        return None, "depth outside well TD"
    return round(md, 1), None


def main(paths: list[str]) -> None:
    hazards = set(taxonomy()["hazards"])
    items = [it for p in paths for it in json.load(open(p))]
    stats: Counter = Counter()
    cx = ctx()
    with SessionLocal() as db:
        for it in items:
            e = db.get(Event, it.get("id"))
            if e is None or not e.needs_review:
                stats["skipped (not in queue)"] += 1
                continue
            d = it.get("decision")
            before = _event_snapshot(e)
            note = f"AI review: {it.get('reason', '')}".strip()
            if d == "reject":
                db.delete(e)
                db.flush()
                _log(e.id, "reject", REVIEWER, note, before, None)
                stats["reject"] += 1
                continue
            if d not in ("confirm", "relabel"):
                stats["skipped (bad decision)"] += 1
                continue
            if d == "relabel":
                h = it.get("hazard")
                if h not in hazards:
                    stats["skipped (bad hazard)"] += 1
                    continue
                e.hazard = h
            w = cx.wells.get(e.well_id)
            md, why = _depth_m(it, e.evidence_span or "", getattr(w, "td_md_m", None))
            if why:
                stats[f"depth dropped: {why}"] += 1
            if md is not None:
                if e.md_m is None:
                    stats["depth added"] += 1
                e.md_m = md
                e.formation = cx.tops.at(e.well_id, md) or e.formation
            elif e.md_m is not None:
                # an auto-extracted depth the reviewer could not verify from the sentence is not kept
                # (some table rows parse an inclination or a mud value as a depth)
                e.md_m = None
                e.formation = None
                stats["unverified depth cleared"] += 1
            e.needs_review = False
            e.method = "ai_review"
            db.flush()
            _log(e.id, d, REVIEWER, note, before, _event_snapshot(e))
            stats[d] += 1
        db.commit()
    caches.reset_all()
    print(json.dumps(dict(stats), indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
