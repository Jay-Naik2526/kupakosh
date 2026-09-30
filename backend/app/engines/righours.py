"""Rig hours at stake: how much logged rig time the real problems cost, and how much of it Kupakosh warned about blind.

Only timed daily drilling reports can answer this. Each Volve report line has a start and end time
("06:00 - 07:30: Worked tight spot at 2993 m ..."), so a trusted problem event on such a line has a
measured duration: the rig time the report itself spent on that line. That is the number used here.

Rules kept:
- Hours are the duration of the report line that records the problem, nothing else. It is a lower bound of
  the time lost (follow-up lines are not added, because a later line can be unrelated routine work).
- A problem counts as "warned" only when the Hindsight blind replay (engines.hindsight, alert mode from
  config) had an alert live for its layer and hazard before the bit reached it, on a model that never
  trained on that well.
- No cost in money: day rates are not in the public data, so the unit stays rig-hours.
- Events on report lines without times (24-hour summaries) are counted separately and never given hours.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select

from app.config import taxonomy
from app.db.models import Activity, Document, Event, Passage, Well
from app.db.session import SessionLocal
from app.engines import hindsight as hs

_CACHE: dict = {}

METHOD = ("Hours are the start-to-end time of the daily-report line that records the problem (Equinor Volve daily "
          "drilling reports, timed activity lines). This is a lower bound of the rig time lost: follow-up lines are not "
          "added. 'Warned' means the Hindsight blind replay had an alert live for that layer and hazard before the bit "
          "reached it, from a model that never trained on that well. Problems on report lines without times are not given "
          "hours. No money figure is shown: day rates are not in the public data.")


def _line_hours(a: Activity) -> float | None:
    if a.t_start is None or a.t_end is None:
        return None
    h = (a.t_end - a.t_start).total_seconds() / 3600
    return round(h, 2) if 0 < h <= 24 else None


def summary(force: bool = False) -> dict:
    s = hs.summary()
    key = (s.get("generated_at"), s.get("engine_version"))
    if not force and _CACHE.get("key") == key:
        return _CACHE["out"]
    tested = {r["well_id"] for r in s.get("wells", [])}
    with SessionLocal() as db:
        rows = db.execute(
            select(Event, Activity, Well.canonical_name, Document.report_date)
            .join(Passage, Passage.id == Event.passage_id).join(Document, Document.id == Passage.document_id)
            .outerjoin(Activity, Activity.id == Event.activity_id).join(Well, Well.id == Event.well_id)
            .where(Document.kind == "DDR_XML", Event.needs_review.is_(False))
        ).all()
        db.expunge_all()
    warned: dict[int, dict] = {}
    for wid in sorted({e.well_id for e, *_ in rows} & tested):
        for ev in hs.run_well(wid)["events"]:
            warned[ev["event_id"]] = ev
    labels = {k: v.get("label", k) for k, v in taxonomy()["hazards"].items()}
    by_h: dict[str, dict] = defaultdict(lambda: {"events": 0, "hours": 0.0, "warned_events": 0, "warned_hours": 0.0})
    tot = {"events_timed": 0, "hours": 0.0, "events_untimed": 0, "in_test": 0, "in_test_hours": 0.0, "warned_events": 0, "warned_hours": 0.0}
    examples = []
    for e, a, wname, day in rows:
        h = _line_hours(a) if a is not None else None
        if h is None:
            tot["events_untimed"] += 1
            continue
        tot["events_timed"] += 1
        tot["hours"] += h
        b = by_h[e.hazard]
        b["events"] += 1
        b["hours"] += h
        w = warned.get(e.id)
        if w is None:
            continue
        tot["in_test"] += 1
        tot["in_test_hours"] += h
        if w["forewarned"]:
            tot["warned_events"] += 1
            tot["warned_hours"] += h
            b["warned_events"] += 1
            b["warned_hours"] += h
            examples.append({"event_id": e.id, "well": wname, "date": day.isoformat() if day else None, "hazard": e.hazard,
                             "label": labels.get(e.hazard, e.hazard), "md_m": e.md_m, "hours": h, "lead_m": w["lead_m"],
                             "formation": w.get("formation_label"), "source_ref": e.source_ref, "evidence": (e.evidence_span or "")[:300]})
    r = lambda x: round(x, 1)
    out = {
        "reports": "Equinor Volve daily drilling reports",
        "events_timed": tot["events_timed"], "hours": r(tot["hours"]), "events_untimed": tot["events_untimed"],
        "in_test": {"events": tot["in_test"], "hours": r(tot["in_test_hours"])},
        "warned": {"events": tot["warned_events"], "hours": r(tot["warned_hours"]),
                   "share_of_hours": round(tot["warned_hours"] / tot["in_test_hours"], 4) if tot["in_test_hours"] else None},
        "by_hazard": sorted(({"hazard": k, "label": labels.get(k, k), **{kk: (r(vv) if isinstance(vv, float) else vv) for kk, vv in v.items()}}
                             for k, v in by_h.items()), key=lambda x: -x["hours"]),
        "examples": sorted(examples, key=lambda x: -x["hours"])[:6],
        "alert_mode": s.get("alert_mode_config"), "method": METHOD,
    }
    _CACHE.update(key=key, out=out)
    return out
