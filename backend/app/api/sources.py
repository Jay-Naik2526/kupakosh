"""Resolve any source_ref to its verbatim evidence (SPEC.md §0.5: every claim is traceable)."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CasingString, Document, FormationTop, MudCheck, Passage, PressureTest, Well


def resolve(db: Session, ref: str) -> dict:
    ref = (ref or "").strip()
    m = re.match(r"^doc:(\d+)#(.+)$", ref)
    if m:
        doc = db.get(Document, int(m.group(1)))
        if not doc:
            return {"ref": ref, "found": False}
        loc = m.group(2)
        well = db.get(Well, doc.well_id) if doc.well_id else None
        base = {"ref": ref, "found": True, "document_id": doc.id, "kind": doc.kind, "title": doc.title, "url": doc.url,
                "path": doc.path, "report_date": doc.report_date.isoformat() if doc.report_date else None,
                "licence": doc.licence, "well": well.canonical_name if well else None, "locator": loc}
        p = db.scalars(select(Passage).where(Passage.document_id == doc.id, Passage.locator == loc)).first()
        if p:
            ctx = db.scalars(select(Passage).where(Passage.document_id == doc.id, Passage.seq.between(p.seq - 1, p.seq + 1)).order_by(Passage.seq)).all()
            return {**base, "text": p.text, "context": [{"locator": c.locator, "text": c.text, "is_target": c.id == p.id} for c in ctx]}
        if loc.startswith("casing:"):
            return {**base, "text": loc[len("casing:"):] + " …", "note": "casing table row on the daily report"}
        if loc in ("mud", "header", "quote"):
            return {**base, "text": None, "note": f"{loc} section of the report (open the PDF at `path`)"}
        return {**base, "text": None}
    m = re.match(r"^sodir:(\w+):(\d+)#(.+)$", ref)
    if m:
        table, npdid, key = m.groups()
        well = db.scalars(select(Well).where(Well.external_id == npdid)).first()
        out = {"ref": ref, "found": well is not None, "kind": f"SODIR_TABLE:{table}", "well": well.canonical_name if well else None,
               "url": well.fact_url if well else None, "licence": "NLOD 2.0", "title": f"Sodir FactPages — {table}"}
        if table == "wellbore_formation_top" and well:
            t = db.scalars(select(FormationTop).where(FormationTop.well_id == well.id, FormationTop.formation == key)).first()
            out["text"] = f"{key}: top {t.top_md_m:g} m, base {t.base_md_m or 0:g} m (MD RKB)" if t else None
        elif table == "wellbore_casing_and_lot" and well:
            cs = db.scalars(select(CasingString).where(CasingString.source_ref == ref)).first()
            pt = db.scalars(select(PressureTest).where(PressureTest.source_ref == ref)).first()
            parts = []
            if cs:
                parts.append(f'{cs.casing_type or "casing"} {cs.od_in or "?"}" at {cs.shoe_md_m or "?"} m, hole {cs.hole_in or "?"}" to {cs.hole_md_m or "?"} m')
            if pt:
                parts.append(f"{pt.kind} {pt.raw_value} g/cm3 = {pt.emw_ppg} ppg EMW")
            out["text"] = "; ".join(parts) or None
        elif table == "wellbore_mud" and well:
            mc = db.scalars(select(MudCheck).where(MudCheck.source_ref == ref)).first()
            out["text"] = f"mud weight {mc.raw_value} g/cm3 ({mc.mw_ppg} ppg) at {mc.md_m:g} m, {mc.mud_type or ''}" if mc else None
        return out
    m = re.match(r"^realtime:(.+)@(.+)$", ref)
    if m:
        return {"ref": ref, "found": True, "kind": "SENSOR", "well": m.group(1), "title": "Pason 10-second rig sensor data (REPLAY source)",
                "text": f"sensor record at {m.group(2)}", "licence": "CC-BY 4.0"}
    if ref.startswith("http"):
        from app.db.models import Basin
        b = db.scalars(select(Basin).where(Basin.url == ref)).first()
        return {"ref": ref, "found": True, "kind": "PUBLIC_WEB_PAGE", "url": ref,
                "title": f"NDR/DGH public page — {b.name}" if b else "Public web page",
                "text": (b.area_text if b and b.area_text else None),
                "note": "Figures quoted from the public page; open the link for the full text.",
                "licence": "Govt. of India public web content" if b else None}
    return {"ref": ref, "found": False, "text": None}
