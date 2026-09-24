"""Sodir FactPages (Norwegian Offshore Directorate) -> wells, tops, casing/LOT, mud, history.

All tables are the public CSV exports downloaded by scripts/download_data.sh.
Licence: Norwegian Licence for Open Government Data (NLOD 2.0).
Validation rules (rejected rows are counted, never "fixed"):
  * mud weight must be within config extract.mw_range_ppg after sg->ppg
  * any depth must be within [0, well TD] when TD is known
  * LOT/FIT density 0.00 means "no test reported" -> no pressure_test row
"""
from __future__ import annotations

import html
import re
from collections import Counter
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.config import RAW_DIR, cfg
from app.db.models import CasingString, Document, Field, FormationTop, MudCheck, Passage, PressureTest, Well
from app.ingest.units import sg_to_ppg, to_float
from app.ingest.well_ids import canonical

SODIR = RAW_DIR / "sodir"
LICENCE = "NLOD 2.0 (Norwegian Licence for Open Government Data)"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(SODIR / f"{name}.csv", encoding="utf-8-sig", low_memory=False, dtype=str, keep_default_na=False)


def _date(s: str):
    s = (s or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def html_to_paragraphs(raw: str) -> list[str]:
    """Sodir history is Word-exported HTML. Split into paragraphs on <p>/<br>, strip tags."""
    raw = raw or ""
    parts = re.split(r"(?i)</p>|<br\s*/?>", raw)
    out = []
    for p in parts:
        t = html.unescape(re.sub(r"<[^>]+>", " ", p))
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            out.append(t)
    return out


_ABBR = r"(?<!\bca)(?<!\bapprox)(?<!\bno)(?<!\bNo)(?<!\bfig)(?<!\be\.g)(?<!\bi\.e)(?<!\bvs)"
_SENT = re.compile(_ABBR + r"(?<=[.!?])\s+(?=[A-Z0-9\"(])")


def split_sentences(par: str) -> list[str]:
    return [s.strip() for s in _SENT.split(par) if s.strip()]


def ingest(db: Session, log=print) -> dict:
    c = cfg()
    mw_lo, mw_hi = c["extract"]["mw_range_ppg"]
    stats: Counter = Counter()

    wells_df = _read("wellbore_all_long")
    fields: dict[str, Field] = {}
    wells: dict[str, Well] = {}
    for r in wells_df.itertuples(index=False):
        name = canonical(r.wlbWellboreName)
        if name in wells:
            continue
        fname = (r.wlbField or "").strip() or None
        fid = None
        if fname:
            if fname not in fields:
                f = Field(name=fname, country="Norway", source="sodir")
                db.add(f)
                db.flush()
                fields[fname] = f
            fid = fields[fname].id
        lat, lon = to_float(r.wlbNsDecDeg), to_float(r.wlbEwDecDeg)
        w = Well(
            canonical_name=name,
            aliases=[r.wlbWellboreName] + ([r.wlbAliasName] if r.wlbAliasName else []),
            field_id=fid, field_name=fname, lat=lat, lon=lon,
            kb_elev_m=to_float(r.wlbKellyBushElevation), water_depth_m=to_float(r.wlbWaterDepth),
            spud_date=_date(r.wlbEntryDate), td_md_m=to_float(r.wlbTotalDepth), td_tvd_m=to_float(r.wlbFinalVerticalDepth),
            status=r.wlbStatus or None, purpose=r.wlbPurpose or None, well_type=r.wlbWellType or None,
            operator=r.wlbDrillingOperator or None, formation_at_td=r.wlbFormationAtTd or None,
            source="sodir", position_source="sodir wellbore_all_long (ED50 decimal degrees)" if lat else None,
            parent_well=canonical(r.wlbWell) if r.wlbWell else None, external_id=r.wlbNpdidWellbore, fact_url=r.wlbFactPageUrl or None,
        )
        db.add(w)
        wells[name] = w
        stats["wells"] += 1
    db.flush()
    log(f"sodir: {stats['wells']} wells, {len(fields)} fields")

    # ---- formation tops (FORMATION + GROUP levels) ----
    tops = _read("wellbore_formation_top")
    rows = []
    for r in tops.itertuples(index=False):
        w = wells.get(canonical(r.wlbName))
        if not w:
            stats["tops_no_well"] += 1
            continue
        if r.lsuLevel not in ("FORMATION", "GROUP"):
            continue
        top, base = to_float(r.lsuTopDepth), to_float(r.lsuBottomDepth)
        rows.append(FormationTop(
            well_id=w.id, formation=r.lsuName.strip(), level=r.lsuLevel,
            grp=(r.lsuNameParent or None) if r.lsuLevel == "FORMATION" else r.lsuName.strip(),
            top_md_m=top, base_md_m=base, source="sodir",
            source_ref=f"sodir:wellbore_formation_top:{w.external_id}#{r.lsuName.strip()}",
        ))
    db.add_all(rows)
    stats["formation_tops"] = len(rows)
    db.flush()
    log(f"sodir: {len(rows)} formation tops")

    # ---- casing + LOT/FIT ----
    cas = _read("wellbore_casing_and_lot")
    cs_rows, pt_rows = [], []
    for i, r in enumerate(cas.itertuples(index=False)):
        w = wells.get(canonical(r.wlbName))
        if not w:
            continue
        ref = f"sodir:wellbore_casing_and_lot:{w.external_id}#row{i}"
        od = _inch(r.wlbCasingDiameter)
        shoe = to_float(r.wlbCasingDepth)
        hole = to_float(r.wlbHoleDepth)
        if shoe is not None and w.td_md_m and shoe > w.td_md_m + 1:
            stats["casing_depth_gt_td"] += 1
            shoe = None
        cs_rows.append(CasingString(
            well_id=w.id, casing_type=(r.wlbCasingType or "").strip() or None, od_in=od, hole_in=_inch(r.wlbHoleDiameter),
            shoe_md_m=shoe or None, hole_md_m=hole or None, source_ref=ref,
        ))
        dens = to_float(r.wlbLotMudDencity)
        kind = (r.wlbFormationTestType or "").strip().upper()
        if dens and dens > 0 and kind in ("LOT", "FIT", "XLOT", "XLO"):
            ppg = sg_to_ppg(dens)
            if not (mw_lo <= ppg <= mw_hi + 4):  # LOT EMW may exceed drilling MW range
                stats["lot_out_of_range"] += 1
                continue
            pt_rows.append(PressureTest(
                well_id=w.id, kind="FIT" if kind == "FIT" else "LOT", md_m=shoe, emw_ppg=round(ppg, 2),
                raw_value=dens, raw_unit="g/cm3", casing_shoe_md_m=shoe, source_ref=ref,
            ))
    db.add_all(cs_rows)
    db.add_all(pt_rows)
    stats["casing_strings"], stats["pressure_tests"] = len(cs_rows), len(pt_rows)
    log(f"sodir: {len(cs_rows)} casing strings, {len(pt_rows)} LOT/FIT")

    # ---- mud weight by depth ----
    mud = _read("wellbore_mud")
    mrows = []
    for i, r in enumerate(mud.itertuples(index=False)):
        w = wells.get(canonical(r.wlbName))
        md, sg = to_float(r.wlbMD), to_float(r.wlbMudWeightAtMD)
        if not w or md is None or sg is None:
            continue
        ppg = sg_to_ppg(sg)
        if not (mw_lo <= ppg <= mw_hi):
            stats["mud_rejected_mw"] += 1
            continue
        if w.td_md_m and md > w.td_md_m + 1:
            stats["mud_rejected_md"] += 1
            continue
        mrows.append(MudCheck(
            well_id=w.id, md_m=md, mw_ppg=round(ppg, 2), raw_value=sg, raw_unit="g/cm3",
            mud_type=r.wlbMudType or None, measured=_date(r.wlbMudDateMeasured),
            source_ref=f"sodir:wellbore_mud:{w.external_id}#row{i}",
        ))
    db.add_all(mrows)
    stats["mud_checks"] = len(mrows)
    log(f"sodir: {len(mrows)} mud checks (rejected mw={stats['mud_rejected_mw']}, md={stats['mud_rejected_md']})")

    # ---- well history narratives -> documents + sentence passages ----
    hist = _read("wellbore_history")
    n_pass = 0
    for r in hist.itertuples(index=False):
        w = wells.get(canonical(r.wlbName))
        if not w:
            continue
        doc = Document(
            well_id=w.id, kind="WELL_HISTORY", title=f"Sodir well history — {w.canonical_name}",
            url=w.fact_url, report_date=_date(r.wlbHistoryDateUpdated), licence=LICENCE,
            sha256=f"sodir-history-{w.external_id}",
        )
        db.add(doc)
        db.flush()
        seq = 0
        for pi, par in enumerate(html_to_paragraphs(r.wlbHistory), start=1):
            for si, sent in enumerate(split_sentences(par), start=1):
                seq += 1
                db.add(Passage(document_id=doc.id, well_id=w.id, locator=f"p{pi}.s{si}", seq=seq, text=sent))
                n_pass += 1
        stats["history_docs"] += 1
    stats["passages"] = n_pass
    db.flush()
    log(f"sodir: {stats['history_docs']} history documents, {n_pass} sentences")
    return dict(stats)


def _inch(s: str) -> float | None:
    """Sodir diameters are strings like '13 3/8', '9 5/8', '30'."""
    s = (s or "").strip()
    if not s:
        return None
    m = re.match(r"^(\d+)(?:\s+(\d+)/(\d+))?$", s)
    if m:
        v = float(m.group(1))
        if m.group(2):
            v += float(m.group(2)) / float(m.group(3))
        return v
    return to_float(s)
