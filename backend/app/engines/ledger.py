"""USP2: outcome-ranked mitigation ledger (SPEC.md §9.3).

For each action type used against a hazard (optionally in one formation / set of wells):
  n     episodes with a known outcome where the action was taken
  k     resolved + partial_credit * partial
  rate  k / n,   lb = Wilson lower bound (z from config)
Episodes whose outcome is 'unknown' are counted separately and never enter the rate.
Rows with n < min_n_display are tagged 'anecdotal'.
"""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import cfg
from app.db.models import Episode


def wilson_lb(k: float, n: int, z: float) -> float:
    if n == 0:
        return 0.0
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def ledger(db: Session, hazard: str | None = None, formation: str | None = None, well_ids: list[int] | None = None,
           country: str | None = None) -> dict:
    c = cfg()["ledger"]
    q = select(Episode)
    if country:  # a join, not an id list: one country can have tens of thousands of wells (SQLite variable limit)
        from app.db.models import Well
        q = q.join(Well, Well.id == Episode.well_id).where(Well.country == country)
    if hazard:
        q = q.where(Episode.hazard == hazard)
    if formation:
        q = q.where(Episode.formation == formation)
    if well_ids is not None:
        q = q.where(Episode.well_id.in_(well_ids))
    eps = db.scalars(q).all()
    rows = defaultdict(lambda: {"episodes": [], "resolved": 0, "partial": 0, "unresolved": 0, "worsened": 0, "unknown": 0, "hours": []})
    for e in eps:
        for a in e.action_types or []:
            r = rows[a]
            r["episodes"].append(e.id)
            r[e.outcome] += 1
            if e.hours_to_resolve is not None:
                r["hours"].append(e.hours_to_resolve)
            elif e.npt_hours is not None and e.outcome in ("resolved", "partial"):
                r["hours"].append(e.npt_hours)
    out = []
    for a, r in rows.items():
        n = r["resolved"] + r["partial"] + r["unresolved"] + r["worsened"]
        k = r["resolved"] + c["partial_credit"] * r["partial"]
        out.append({
            "action": a, "n": n, "k": k, "rate": round(k / n, 4) if n else None,
            "lb": round(wilson_lb(k, n, c["z"]), 4) if n else None,
            "resolved": r["resolved"], "partial": r["partial"], "unresolved": r["unresolved"], "worsened": r["worsened"],
            "unknown_outcome": r["unknown"], "median_hours": round(median(r["hours"]), 1) if r["hours"] else None,
            "anecdotal": n < c["min_n_display"], "episode_ids": r["episodes"],
        })
    out.sort(key=lambda r: (r["lb"] is None, -(r["lb"] or 0), -r["n"]))
    known = sum(1 for e in eps if e.outcome != "unknown")
    return {"hazard": hazard, "formation": formation, "n_episodes": len(eps), "n_known_outcome": known, "rows": out}
