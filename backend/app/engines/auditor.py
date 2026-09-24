"""USP4: report auditor — flags where sources disagree (SPEC.md §9.9).

Rules implemented on the real data we have:
  R1 ddr_loss_vs_pit      DDR says losses at time t; sensor pit volume shows no drop around t (FORGE)
  R2 casing_shoe          casing depth stated in well-history text vs Sodir casing table (Sodir);
                          casing shoe reported differently across daily reports of one well (FORGE)
  R3 formation_top        'top of X Formation at N m' in history text vs Sodir formation-top table
  R6 ddr_depth_vs_sensor  depth on the daily report vs sensor hole depth at report time (FORGE)
Tolerances come from config `auditor`. Every flag carries both claims and both references.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import cfg
from app.db.models import AuditFlag, CasingString, Document, Event, FormationTop, Passage, RealtimeSample, Well
from app.ingest.units import ft_to_m

_CASING_TXT = re.compile(r"(\d{1,2}(?: \d/\d{1,2})?)\s?(?:\"|”|''|inch|in\.?)\s*(?:casing|liner|conductor)\b[^.]{0,60}?\b(?:set|landed|cemented|run|installed)\b[^.]{0,25}?\b(?:at|to|in|@)\s+(\d{2,4}(?:\.\d)?)\s?m\b", re.I)
_TOP_TXT = re.compile(r"\btop (?:of )?(?:the )?([A-ZÆØÅ][a-zæøåA-ZÆØÅ]+)\s+(Formation|Group|Fm)\b[^.;]{0,40}?\b(?:at|was at|came in at|encountered at|penetrated at)\s+(\d{3,4}(?:\.\d)?)\s?m\b(?!\s*(?:TVD|MSL|below sea|bsl))")


def _frac(s: str) -> float:
    parts = s.split()
    v = float(parts[0])
    if len(parts) > 1:
        a, b = parts[1].split("/")
        v += float(a) / float(b)
    return v


def run(db: Session, log=print) -> dict:
    c = cfg()["auditor"]
    tol = c["depth_tol_m"]
    db.execute(delete(AuditFlag))
    db.flush()
    wells = {w.id: w for w in db.scalars(select(Well))}
    counts = defaultdict(int)

    # ---- R2 (Sodir): casing depth in text vs casing table ----
    cas = defaultdict(list)
    for cs in db.scalars(select(CasingString).where(CasingString.shoe_md_m.is_not(None))):
        cas[cs.well_id].append(cs)
    tops = defaultdict(dict)
    for t in db.scalars(select(FormationTop).where(FormationTop.source == "sodir")):
        tops[t.well_id][t.formation] = t
    hist = select(Passage, Document).join(Document).where(Document.kind == "WELL_HISTORY")
    for p, d in db.execute(hist):
        for m in _CASING_TXT.finditer(p.text):
            od, md = _frac(m.group(1)), float(m.group(2))
            cands = [x for x in cas.get(p.well_id, []) if x.od_in and abs(x.od_in - od) < 0.01]
            if not cands:
                continue
            best = min(cands, key=lambda x: abs(x.shoe_md_m - md))
            delta = md - best.shoe_md_m
            if abs(delta) > tol:
                db.add(AuditFlag(well_id=p.well_id, rule="R2_casing_shoe", severity="medium",
                                 claim_a=f'{m.group(1)}" casing at {md:g} m (well history text): "{p.text}"', ref_a=f"doc:{d.id}#{p.locator}",
                                 claim_b=f'{best.od_in:g}" {best.casing_type or "casing"} at {best.shoe_md_m:g} m (Sodir casing table)', ref_b=best.source_ref,
                                 delta=f"{delta:+.0f} m"))
                counts["R2_casing_shoe"] += 1
        # ---- R3: formation top in text vs table ----
        for m in _TOP_TXT.finditer(p.text):
            name, kind, md = m.group(1).upper(), m.group(2), float(m.group(3))
            key = f"{name} {'GP' if kind == 'Group' else 'FM'}"
            t = tops.get(p.well_id, {}).get(key)
            if t is None or t.top_md_m is None:
                continue
            delta = md - t.top_md_m
            if abs(delta) > tol:
                db.add(AuditFlag(well_id=p.well_id, rule="R3_formation_top", severity="low" if abs(delta) < 3 * tol else "medium",
                                 claim_a=f"top {m.group(1)} {kind} at {md:g} m (well history text): \"{p.text}\"", ref_a=f"doc:{d.id}#{p.locator}",
                                 claim_b=f"{key} top at {t.top_md_m:g} m MD (Sodir formation-top table)", ref_b=t.source_ref,
                                 delta=f"{delta:+.0f} m"))
                counts["R3_formation_top"] += 1

    # ---- FORGE rules (DDR vs DDR, DDR vs sensors) ----
    forge = [w for w in wells.values() if w.source == "forge"]
    for w in forge:
        # R2b: casing shoe reported differently across daily reports
        by = defaultdict(list)
        for cs in cas.get(w.id, []):
            by[(cs.casing_type, cs.od_in)].append(cs)
        for (ctype, od), lst in by.items():
            vals = sorted({round(x.shoe_md_m, 1) for x in lst})
            if len(vals) > 1 and vals[-1] - vals[0] > 0.5:
                a = next(x for x in lst if round(x.shoe_md_m, 1) == vals[0])
                b = next(x for x in lst if round(x.shoe_md_m, 1) == vals[-1])
                sev = "medium" if vals[-1] - vals[0] > tol else "low"
                db.add(AuditFlag(well_id=w.id, rule="R4_same_quantity_differs", severity=sev,
                                 claim_a=f"{ctype} {od:g}\" shoe at {a.shoe_md_m / 0.3048:,.0f} ft", ref_a=a.source_ref,
                                 claim_b=f"{ctype} {od:g}\" shoe at {b.shoe_md_m / 0.3048:,.0f} ft", ref_b=b.source_ref,
                                 delta=f"{(vals[-1] - vals[0]) / 0.3048:+.0f} ft across daily reports"))
                counts["R4_same_quantity_differs"] += 1
        rt = db.execute(select(RealtimeSample.t, RealtimeSample.md_m, RealtimeSample.pit_vol).where(RealtimeSample.well_id == w.id).order_by(RealtimeSample.t)).all()
        if not rt:
            continue
        ts = [r[0] for r in rt]
        import bisect

        # R6: report depth vs sensor depth at 06:00 of the report date
        for d in db.scalars(select(Document).where(Document.well_id == w.id, Document.kind == "DDR_PDF")):
            md_txt = _report_depth(db, d)
            if md_txt is None:
                continue
            t_end = datetime.combine(d.report_date, datetime.min.time()) + timedelta(hours=6)
            i = bisect.bisect_right(ts, t_end) - 1
            if i < 0 or (t_end - ts[i]) > timedelta(hours=2):
                continue
            sensor = max((r[1] or 0) for r in rt[max(0, i - 360):i + 1])
            delta = md_txt - sensor
            if abs(delta) > tol:
                db.add(AuditFlag(well_id=w.id, rule="R6_ddr_depth_vs_sensor", severity="low",
                                 claim_a=f"Daily report {d.report_date}: depth {md_txt / 0.3048:,.0f} ft", ref_a=f"doc:{d.id}#header",
                                 claim_b=f"Sensor hole depth at 06:00: {sensor / 0.3048:,.0f} ft", ref_b=f"realtime:{w.canonical_name}@{ts[i].isoformat()}",
                                 delta=f"{delta:+.0f} m"))
                counts["R6_ddr_depth_vs_sensor"] += 1

        # R1: DDR losses vs pit-volume drop
        for e in db.scalars(select(Event).where(Event.well_id == w.id, Event.hazard == "lost_circulation", Event.t.is_not(None))):
            lo = bisect.bisect_left(ts, e.t - timedelta(minutes=c["time_tol_min"]))
            hi = bisect.bisect_right(ts, e.t + timedelta(hours=6))
            pits = [r[2] for r in rt[lo:hi] if r[2] is not None]
            if len(pits) < 10:
                continue
            drop = max(pits) - min(pits[pits.index(max(pits)):] or [max(pits)])
            if drop < c["pit_drop_bbl"]:
                db.add(AuditFlag(well_id=w.id, rule="R1_ddr_loss_vs_pit", severity="low",
                                 claim_a=f"DDR reports losses: \"{e.evidence_span[:220]}\"", ref_a=e.source_ref,
                                 claim_b=f"Sensor pit volume dropped at most {drop:.1f} bbl in the 6 h after", ref_b=f"realtime:{w.canonical_name}@{e.t.isoformat()}",
                                 delta=f"pit drop {drop:.1f} bbl < {c['pit_drop_bbl']} bbl"))
                counts["R1_ddr_loss_vs_pit"] += 1
    db.flush()
    log(f"auditor: {dict(counts)}")
    return dict(counts)


def _report_depth(db: Session, d: Document) -> float | None:
    return d.report_md_m


def trust_for_refs(db: Session, refs: list[str]) -> float | None:
    """Share of cited references with no open audit conflict (1.0 = nothing disputed)."""
    if not refs:
        return None
    flagged = set()
    for f in db.scalars(select(AuditFlag).where(AuditFlag.status == "open")):
        flagged.add(f.ref_a.split("#")[0])
        flagged.add(f.ref_b.split("#")[0])
    ok = sum(1 for r in refs if r.split("#")[0] not in flagged)
    return round(ok / len(refs), 3)
