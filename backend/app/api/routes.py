"""REST API (SPEC.md §10)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.sources import resolve
from app.config import cfg, lithology, taxonomy
from app.db.models import (AuditFlag, CasingString, DataSource, Document, Episode, EvalResult, Event, FormationTop, MudCheck,
                           Passage, PressureTest, RealtimeSample, SurveyStation, Well, WikiPage)
from app.db.session import get_db
from app.engines import hazard as hz
from app.engines import mudwindow as mw
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.ledger import ledger as ledger_fn
from app.engines.lookahead import formation_intervals
from app.engines.offsets import find_offsets, offsets_for_well

router = APIRouter(prefix="/api")


def _well(db: Session, well_id: int) -> Well:
    w = db.get(Well, well_id)
    if not w:
        raise HTTPException(404, "well not found")
    return w


# rows that are locations, not wells: BSEE block aggregates, field centroids (never counted as wells)
NOT_WELLS = ("block_aggregate", "field_centroid")


def _country_ids(db: Session, country: str | None) -> set[int] | None:
    """Well ids of one country (None = no filter). Country names are the English names stored on well.country."""
    if not country:
        return None
    return set(db.scalars(select(Well.id).where(Well.country == country)))


def _w(w: Well) -> dict:
    cx = ctx()
    return {"id": w.id, "name": w.canonical_name, "field": w.field_name, "country": w.country, "lat": w.lat, "lon": w.lon, "td_md_m": w.td_md_m,
            "td_tvd_m": w.td_tvd_m, "spud_date": w.spud_date.isoformat() if w.spud_date else None, "status": w.status,
            "purpose": w.purpose, "type": w.well_type, "operator": w.operator, "source": w.source,
            "documented": w.id in cx.documented, "n_events": len(cx.events.get(w.id, [])), "fact_url": w.fact_url,
            "water_depth_m": w.water_depth_m, "kb_elev_m": w.kb_elev_m, "parent_well": w.parent_well}


@router.get("/config")
def get_config():
    c = cfg()
    tax = taxonomy()
    return {"hazards": {k: {"label": v["label"], "glyph": tax["glyphs"].get(k)} for k, v in tax["hazards"].items()},
            "actions": list(tax["actions"].keys()), "ui": c["ui"], "demo_users": c["demo"]["users"],
            "offsets": c["offsets"], "hazard": c["hazard"], "lookahead": c["lookahead"], "replay": c["replay"]}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    n = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w)) or 0
    evals = [{"name": e.name, "metric": e.metric, "value": e.value, "n": e.n, "run_at": e.run_at.isoformat() if e.run_at else None, "notes": e.notes}
             for e in db.scalars(select(EvalResult).order_by(EvalResult.id))]
    return {
        "counts": {
            "wells": n(Well, Well.well_type.is_(None) | Well.well_type.not_in(NOT_WELLS)),
            "aggregate_locations": n(Well, Well.well_type.in_(NOT_WELLS)), "documented_wells": len(ctx().documented), "formation_tops": n(FormationTop),
            "documents": n(Document), "report_entries": n(Passage), "ddr_reports": n(Document, Document.kind.in_(("DDR_PDF", "DDR_XML"))),
            "history_documents": n(Document, Document.kind == "WELL_HISTORY"), "events": n(Event),
            "events_trusted": n(Event, Event.needs_review.is_(False)), "events_needs_review": n(Event, Event.needs_review.is_(True)),
            "episodes": n(Episode), "episodes_known_outcome": n(Episode, Episode.outcome != "unknown"),
            "lot_fit": n(PressureTest), "casing_strings": n(CasingString), "mud_checks": n(MudCheck),
            "survey_stations": n(SurveyStation), "realtime_samples": n(RealtimeSample),
            "audit_open": n(AuditFlag, AuditFlag.status == "open"), "audit_resolved": n(AuditFlag, AuditFlag.status != "open"),
            "wiki_pages": n(WikiPage), "wiki_approved": n(WikiPage, WikiPage.status == "approved"),
        },
        "sources": [{"name": s.name, "url": s.url, "licence": s.licence, "records": s.records,
                     "loaded_at": s.loaded_at.isoformat() if s.loaded_at else None, "notes": s.notes} for s in db.scalars(select(DataSource))],
        "evals": evals,
        "extraction_method": "rule" if not db.scalar(select(func.count()).select_from(Event).where(Event.method != "rule")) else "rule+llm",
        "demo_users": cfg()["demo"]["users"],
        "by_country": countries(db),
    }


@router.get("/countries")
def countries(db: Session = Depends(get_db)):
    """Per-country record counts (drives the country filter chips)."""
    def per(stmt):
        return {c: k for c, k in db.execute(stmt)}
    real = Well.well_type.is_(None) | Well.well_type.not_in(NOT_WELLS)
    wells_n = per(select(Well.country, func.count()).where(real).group_by(Well.country))
    located = per(select(Well.country, func.count()).where(Well.lat.is_not(None)).group_by(Well.country))
    docs = per(select(Well.country, func.count(func.distinct(Passage.document_id))).join(Passage, Passage.well_id == Well.id)
               .group_by(Well.country))
    evs = per(select(Well.country, func.count()).join(Event, Event.well_id == Well.id).group_by(Well.country))
    eps = per(select(Well.country, func.count()).join(Episode, Episode.well_id == Well.id).group_by(Well.country))
    out = [{"country": c or "unknown", "wells": k, "located_wells": located.get(c, 0), "documents_linked": docs.get(c, 0),
            "events": evs.get(c, 0), "episodes": eps.get(c, 0)} for c, k in wells_n.items()]
    out.sort(key=lambda r: (r["country"] != "India", -r["events"], -r["wells"]))
    return out


@router.get("/wells")
def wells(q: str | None = None, bbox: str | None = None, documented: bool = False, field: str | None = None,
          country: str | None = None, located: bool = True, limit: int = 200, db: Session = Depends(get_db)):
    s = select(Well)
    if located:
        s = s.where(Well.lat.is_not(None))
    if country:
        s = s.where(Well.country == country)
    if q:
        s = s.where(or_(Well.canonical_name.ilike(f"%{q}%"), Well.field_name.ilike(f"%{q}%")))
    if field:
        s = s.where(Well.field_name == field)
    if bbox:
        a, b, c, d = map(float, bbox.split(","))  # minLon,minLat,maxLon,maxLat
        s = s.where(Well.lon.between(a, c), Well.lat.between(b, d))
    rows = [_w(w) for w in db.scalars(s.order_by(Well.canonical_name).limit(5000))]
    if documented:
        rows = [r for r in rows if r["documented"]]
    rows.sort(key=lambda r: (not r["documented"], -r["n_events"], r["name"]))
    return rows[:limit]


@router.get("/wells/{well_id}")
def well(well_id: int, db: Session = Depends(get_db)):
    w = _well(db, well_id)
    tops = [{"formation": t.formation, "label": pretty(t.formation), "level": t.level, "top_md_m": t.top_md_m, "base_md_m": t.base_md_m,
             "lithology": t.lithology or lithology().get(t.formation), "source_ref": t.source_ref} for t in ctx().tops.tops(well_id)]
    seen = set()
    casing = []
    for c in db.scalars(select(CasingString).where(CasingString.well_id == well_id).order_by(CasingString.shoe_md_m)):
        k = (c.od_in, round(c.shoe_md_m or 0))
        if k in seen:
            continue
        seen.add(k)
        casing.append({"type": c.casing_type, "od_in": c.od_in, "shoe_md_m": c.shoe_md_m, "formation": c.formation, "source_ref": c.source_ref})
    tests = [{"kind": p.kind, "md_m": p.md_m, "emw_ppg": p.emw_ppg, "formation": p.formation, "source_ref": p.source_ref}
             for p in db.scalars(select(PressureTest).where(PressureTest.well_id == well_id).order_by(PressureTest.md_m))]
    docs = [{"id": d.id, "kind": d.kind, "title": d.title, "report_date": d.report_date.isoformat() if d.report_date else None, "url": d.url}
            for d in db.scalars(select(Document).where(Document.well_id == well_id).order_by(Document.report_date))]
    has_rt = db.scalar(select(func.count()).select_from(RealtimeSample).where(RealtimeSample.well_id == well_id)) or 0
    return {**_w(w), "tops": tops, "casing": casing, "pressure_tests": tests, "documents": docs, "realtime_samples": has_rt}


@router.get("/wells/{well_id}/offsets")
def offsets(well_id: int, radius_m: float | None = None, documented_only: bool = False, country: str | None = None,
            db: Session = Depends(get_db)):
    _well(db, well_id)
    offs = offsets_for_well(well_id, radius_m, documented_only)
    ids = _country_ids(db, country)
    if ids is not None:
        offs = [o for o in offs if o["well_id"] in ids]
    return {"radius_m": radius_m or cfg()["offsets"]["default_radius_m"], "offsets": offs}


@router.get("/wells/{well_id}/section")
def section(well_id: int, radius_m: float | None = None, n: int = 6, db: Session = Depends(get_db)):
    """Correlation panel: the well + up to n-1 documented offsets, each with tops and events by depth."""
    w = _well(db, well_id)
    offs = [o for o in offsets_for_well(well_id, radius_m, documented_only=True)][: max(0, n - 1)]
    cols = []
    for wid, meta in [(well_id, None)] + [(o["well_id"], o) for o in offs]:
        ww = db.get(Well, wid)
        evs = [{"id": e.id, "hazard": e.hazard, "md_m": e.md_m, "formation": e.formation, "confidence": e.confidence,
                "needs_review": e.needs_review, "source_ref": e.source_ref, "evidence": e.evidence_span}
               for e in db.scalars(select(Event).where(Event.well_id == wid, Event.md_m.is_not(None)).order_by(Event.md_m))]
        cols.append({"well": _w(ww), "offset": meta, "tops": formation_intervals(wid), "events": evs})
    return {"columns": cols}


@router.get("/wells/{well_id}/hazards")
def hazards(well_id: int, radius_m: float | None = None, db: Session = Depends(get_db)):
    _well(db, well_id)
    offs = offsets_for_well(well_id, radius_m)
    forms = []
    for t in formation_intervals(well_id):
        if t["formation"] not in forms:
            forms.append(t["formation"])
    prof = hz.profile(forms, offs)
    return {"n_offsets": len(offs), "profile": prof}


@router.get("/hazard_at")
def hazard_at(lat: float, lon: float, formation: str, hazard: str, radius_m: float | None = None, db: Session = Depends(get_db)):
    offs = find_offsets(lat, lon, radius_m)
    return hz.posterior(formation, hazard, offs)


@router.get("/events")
def events(well: int | None = None, hazard: str | None = None, formation: str | None = None, include_review: bool = True,
           country: str | None = None, limit: int = 200, db: Session = Depends(get_db)):
    s = select(Event, Well.canonical_name, Well.country).join(Well, Well.id == Event.well_id)
    if country:
        s = s.where(Well.country == country)
    if well:
        s = s.where(Event.well_id == well)
    if hazard:
        s = s.where(Event.hazard == hazard)
    if formation:
        s = s.where(Event.formation == formation)
    if not include_review:
        s = s.where(Event.needs_review.is_(False))
    out = []
    for e, name, cc in db.execute(s.order_by(Event.well_id, Event.md_m).limit(limit)):
        out.append({"id": e.id, "well_id": e.well_id, "well": name, "country": cc, "hazard": e.hazard, "md_m": e.md_m, "formation": e.formation,
                    "formation_label": pretty(e.formation), "t": e.t.isoformat() if e.t else None, "severity": e.severity,
                    "quantity": e.quantity, "quantity_unit": e.quantity_unit, "mud_weight_ppg": e.mud_weight_ppg,
                    "mud_weight_source": e.mud_weight_source, "confidence": e.confidence, "method": e.method,
                    "needs_review": e.needs_review, "evidence": e.evidence_span, "source_ref": e.source_ref})
    return out


@router.get("/episodes")
def episodes(hazard: str | None = None, formation: str | None = None, action: str | None = None, ids: str | None = None,
             country: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    s = select(Episode, Event, Well.canonical_name).join(Event, Event.id == Episode.event_id).join(Well, Well.id == Episode.well_id)
    if country:
        s = s.where(Well.country == country)
    if ids:
        s = s.where(Episode.id.in_([int(x) for x in ids.split(",") if x]))
    if hazard:
        s = s.where(Episode.hazard == hazard)
    if formation:
        s = s.where(Episode.formation == formation)
    out = []
    for ep, ev, name in db.execute(s.limit(2000)):
        if action and action not in (ep.action_types or []):
            continue
        acts = []
        if ep.action_ids:
            from app.db.models import Action
            for a in db.scalars(select(Action).where(Action.id.in_(ep.action_ids))):
                acts.append({"type": a.action_type, "detail": a.detail, "source_ref": a.source_ref})
        out.append({"id": ep.id, "well": name, "well_id": ep.well_id, "hazard": ep.hazard, "formation": ep.formation,
                    "formation_label": pretty(ep.formation), "md_m": ep.md_m, "outcome": ep.outcome, "outcome_ref": ep.outcome_ref,
                    "outcome_text": ep.outcome_text, "hours_to_resolve": ep.hours_to_resolve, "npt_hours": ep.npt_hours,
                    "confidence": ep.confidence, "event": {"text": ev.evidence_span, "source_ref": ev.source_ref, "t": ev.t.isoformat() if ev.t else None},
                    "actions": acts})
        if len(out) >= limit:
            break
    return out


@router.get("/ledger")
def ledger(hazard: str | None = None, formation: str | None = None, well: int | None = None, radius_m: float | None = None,
           country: str | None = None, db: Session = Depends(get_db)):
    well_ids = None
    if well:
        well_ids = [well] + [o["well_id"] for o in offsets_for_well(well, radius_m)]
    L = ledger_fn(db, hazard, formation, well_ids, country)
    L["country"] = country
    L["formation_label"] = pretty(formation)
    return L


@router.get("/formations")
def formations(hazard: str | None = None, min_wells: int = 3, country: str | None = None, db: Session = Depends(get_db)):
    cx = ctx()
    ids = _country_ids(db, country)
    out = []
    for f, ws in cx.penetrated.items():
        if ids is not None:
            ws = {w for w in ws if w in ids}
        if len(ws) < min_wells:
            continue
        n_ev = sum(1 for (w, ff, h) in cx.ev_wf if ff == f and (hazard is None or h == hazard) and (ids is None or w in ids))
        out.append({"formation": f, "label": pretty(f), "n_wells": len(ws), "n_well_events": n_ev})
    out.sort(key=lambda r: (-r["n_well_events"], -r["n_wells"]))
    return out


@router.get("/mudwindow")
def mudwindow(well: int, formation: str | None = None, radius_m: float | None = None, db: Session = Depends(get_db)):
    _well(db, well)
    ids = [o["well_id"] for o in offsets_for_well(well, radius_m)]
    res = mw.window(db, ids + [well], formation, active_well_id=well)
    res["casing_lessons"] = mw.casing_lessons(db, ids + [well])
    res["tops"] = formation_intervals(well)
    return res


@router.get("/audit")
def audit(well: int | None = None, status: str | None = None, rule: str | None = None, country: str | None = None,
          db: Session = Depends(get_db)):
    s = select(AuditFlag, Well.canonical_name).join(Well, Well.id == AuditFlag.well_id, isouter=True)
    if country:
        s = s.where(Well.country == country)
    if well:
        s = s.where(AuditFlag.well_id == well)
    if status:
        s = s.where(AuditFlag.status == status)
    if rule:
        s = s.where(AuditFlag.rule == rule)
    return [{"id": f.id, "well": name, "well_id": f.well_id, "rule": f.rule, "severity": f.severity, "claim_a": f.claim_a, "ref_a": f.ref_a,
             "claim_b": f.claim_b, "ref_b": f.ref_b, "delta": f.delta, "status": f.status, "reviewer_note": f.reviewer_note,
             "resolved_by": f.resolved_by} for f, name in db.execute(s.order_by(AuditFlag.id))]


class Resolve(BaseModel):
    decision: str  # accept_a | accept_b | uncertain
    reviewer: str
    note: str | None = None


@router.post("/audit/{flag_id}/resolve")
def audit_resolve(flag_id: int, body: Resolve, db: Session = Depends(get_db)):
    f = db.get(AuditFlag, flag_id)
    if not f:
        raise HTTPException(404)
    if body.decision not in ("accept_a", "accept_b", "uncertain"):
        raise HTTPException(422, "decision must be accept_a | accept_b | uncertain")
    f.status, f.reviewer_note, f.resolved_by = body.decision, body.note, body.reviewer
    db.commit()
    return {"ok": True, "id": f.id, "status": f.status}


@router.get("/source")
def source(ref: str, db: Session = Depends(get_db)):
    return resolve(db, ref)


@router.get("/replay/{well_id}/range")
def replay_range(well_id: int, db: Session = Depends(get_db)):
    r = db.execute(select(func.min(RealtimeSample.t), func.max(RealtimeSample.t), func.count(), func.max(RealtimeSample.md_m))
                   .where(RealtimeSample.well_id == well_id)).one()
    return {"t_min": r[0].isoformat() if r[0] else None, "t_max": r[1].isoformat() if r[1] else None, "n": r[2], "max_md_m": r[3]}


@router.get("/replay/wells")
def replay_wells(db: Session = Depends(get_db)):
    rows = db.execute(select(RealtimeSample.well_id, func.count()).group_by(RealtimeSample.well_id)).all()
    return [{**_w(db.get(Well, wid)), "samples": n} for wid, n in rows]


@router.get("/wells/{well_id}/survey")
def survey(well_id: int, db: Session = Depends(get_db)):
    return [{"md_m": s.md_m, "inc_deg": s.inc_deg, "azi_deg": s.azi_deg, "tvd_m": s.tvd_m, "north_m": s.north_m, "east_m": s.east_m}
            for s in db.scalars(select(SurveyStation).where(SurveyStation.well_id == well_id).order_by(SurveyStation.md_m))]
