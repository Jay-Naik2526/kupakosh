"""USP3: offset mud-weight window + casing/cement lessons (SPEC.md §9.8).

Per formation, from offset wells:
  upper evidence  LOT/FIT equivalent mud weight at shoes in the formation; mud weight at recorded losses
  lower evidence  mud weight at recorded kicks / overpressure (the weight that was NOT enough)
  window          [max(lower), min(upper)]; if lower > upper the evidence conflicts and we say so
Also reported: the mud weights actually used in the formation (p10-p90 of mud checks) as context.
Depths are MD. Sodir exploration wells are mostly near-vertical; for deviated wells MD != TVD
and the window is approximate (stated in the response).
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CasingString, Event, MudCheck, PressureTest
from app.engines.context import ctx
from app.engines.formations import pretty


def window(db: Session, well_ids: list[int], formation: str | None = None, active_well_id: int | None = None) -> dict:
    cx = ctx()
    wset = set(well_ids)
    ev = defaultdict(lambda: {"upper": [], "lower": [], "used": [], "tops": [], "bases": []})

    for pt in db.scalars(select(PressureTest).where(PressureTest.well_id.in_(wset))):
        if pt.formation and (formation is None or pt.formation == formation):
            ev[pt.formation]["upper"].append(_pt(pt, cx))
    for e in db.scalars(select(Event).where(Event.well_id.in_(wset), Event.mud_weight_ppg.is_not(None), Event.needs_review.is_(False))):
        if not e.formation or (formation and e.formation != formation):
            continue
        item = {"kind": e.hazard, "md_m": e.md_m, "ppg": e.mud_weight_ppg, "well": cx.wells[e.well_id].canonical_name,
                "source_ref": e.source_ref, "mw_source": e.mud_weight_source, "event_id": e.id}
        if e.hazard == "lost_circulation":
            ev[e.formation]["upper"].append(item)
        elif e.hazard in ("kick", "overpressure"):
            ev[e.formation]["lower"].append(item)
    for m in db.scalars(select(MudCheck).where(MudCheck.well_id.in_(wset))):
        f = cx.tops.at(m.well_id, m.md_m)
        if f and (formation is None or f == formation):
            ev[f]["used"].append(m.mw_ppg)
    for wid in wset:
        for t in cx.tops.tops(wid):
            if t.formation in ev and t.top_md_m is not None:
                ev[t.formation]["tops"].append(t.top_md_m)
                if t.base_md_m:
                    ev[t.formation]["bases"].append(t.base_md_m)

    rows = []
    for f, d in ev.items():
        if not d["upper"] and not d["lower"]:
            continue
        lo = max((x["ppg"] for x in d["lower"]), default=None)
        hi = min((x["ppg"] for x in d["upper"]), default=None)
        status = "window" if lo is not None and hi is not None and lo < hi else \
                 "conflict" if lo is not None and hi is not None else \
                 "upper_only" if hi is not None else "lower_only"
        used = np.array(d["used"]) if d["used"] else None
        rows.append({
            "formation": f, "label": pretty(f), "lower_ppg": lo, "upper_ppg": hi, "status": status,
            "top_md_m": float(np.median(d["tops"])) if d["tops"] else None,
            "base_md_m": float(np.median(d["bases"])) if d["bases"] else None,
            "used_p10_p90": [round(float(np.percentile(used, 10)), 2), round(float(np.percentile(used, 90)), 2)] if used is not None and len(used) >= 3 else None,
            "n_used": len(d["used"]),
            "upper_evidence": sorted(d["upper"], key=lambda x: x["ppg"]),
            "lower_evidence": sorted(d["lower"], key=lambda x: -x["ppg"]),
        })
    rows.sort(key=lambda r: (r["top_md_m"] is None, r["top_md_m"] or 0))
    active = None
    if active_well_id:
        active = [{"md_m": m.md_m, "ppg": m.mw_ppg, "source_ref": m.source_ref}
                  for m in db.scalars(select(MudCheck).where(MudCheck.well_id == active_well_id).order_by(MudCheck.md_m))]
    return {"formations": rows, "active_well_mw": active, "n_offset_wells": len(wset),
            "note": "Depths are MD; for deviated wells the window is approximate. Loss/kick mud weights come from report text or the nearest mud-table reading (see mw_source)."}


def _pt(pt: PressureTest, cx) -> dict:
    return {"kind": pt.kind, "md_m": pt.md_m, "ppg": pt.emw_ppg, "raw": f"{pt.raw_value} {pt.raw_unit}",
            "well": cx.wells[pt.well_id].canonical_name, "source_ref": pt.source_ref}


def casing_lessons(db: Session, well_ids: list[int]) -> list[dict]:
    """Casing shoes by formation + cementing-issue events near each shoe."""
    cx = ctx()
    cem = defaultdict(list)
    for e in db.scalars(select(Event).where(Event.well_id.in_(well_ids), Event.hazard == "cementing_issue")):
        cem[e.well_id].append(e)
    out = []
    seen = set()
    for cs in db.scalars(select(CasingString).where(CasingString.well_id.in_(well_ids), CasingString.shoe_md_m.is_not(None))):
        key = (cs.well_id, cs.od_in, round(cs.shoe_md_m or 0))
        if key in seen:
            continue  # FORGE DDRs repeat the casing table every day
        seen.add(key)
        issues = [{"md_m": e.md_m, "source_ref": e.source_ref, "text": e.evidence_span} for e in cem.get(cs.well_id, [])
                  if e.md_m is None or abs((e.md_m or 0) - cs.shoe_md_m) < 300]
        out.append({"well": cx.wells[cs.well_id].canonical_name, "casing": cs.casing_type, "od_in": cs.od_in,
                    "shoe_md_m": cs.shoe_md_m, "formation": cs.formation, "label": pretty(cs.formation),
                    "cement_issues": issues, "source_ref": cs.source_ref})
    out.sort(key=lambda r: (r["shoe_md_m"] or 0))
    return out
