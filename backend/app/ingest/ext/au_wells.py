"""Australia (public, no-login) -> wells, well-completion-report passages, casing/LOT where stated.

Sources (both fetched with no account; see data/raw/australia/REPORT.md for how):
  * SARIG (Dept. for Energy and Mining, South Australia) WFS `drillholes:petroleum_wells` — a live,
    unauthenticated GeoServer feature layer, downloaded whole as GeoJSON: ~3,986 SA petroleum wells
    with coordinates, TD, operator, basin, spud/rig-release dates. NLOD-style open government data.
  * GSQ Open Data Portal (Geological Survey of Queensland) — CKAN `package_search` over report-type
    packages tagged `well-completion-report`, filtered to commodity petroleum/oil/gaseous-hydrocarbons
    (coal-seam-gas WCRs are excluded). A sample of the PDF body of each report was downloaded (the
    portal's bulk "add to cart" dataset export queues delivery over days by email, so this ingester
    uses the per-report resource download instead, which is instant). CC-BY 4.0.
Both are real Australian public data; no rows are invented. WA WAPIMS, Qld QDEX/GSQ dataset cart,
SA PEPS-SA report ZIPs, NT GEMIS and Vic Earth Resources were checked but needed either a login, an
interactive per-well request form, or the same AWS-WAF-gated bulk endpoint the QPED zip sits behind
(see REPORT.md) — none of those were pulled in this pass.

Well-name dedup: SARIG well names and GSQ WCR titles never collide (different states), but the same
normalisation (`_norm`) is applied before insert so a re-run, or a future third AU source, merges
correctly instead of creating duplicate wells.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from app.ingest.pdftext import pdf_pages_with_conf
from sqlalchemy.orm import Session

from app.config import RAW_DIR, cfg
from app.db.models import CasingString, DataSource, Document, Field, Passage, PressureTest, Well
from app.ingest.india_docs import _paragraphs
from app.ingest.sodir import split_sentences
from app.ingest.units import sg_to_ppg

SOURCE = {"name": "SARIG (SA) + GSQ Open Data Portal (Qld) — Australian public petroleum well data",
          "country": "Australia", "url": "https://sarig.pir.sa.gov.au/ ; https://geoscience.data.qld.gov.au/",
          "licence": "SARIG: CC-BY 4.0 (Govt. of South Australia) ; GSQ Open Data Portal: CC-BY 4.0",
          "raw_dir": "australia"}

AU = RAW_DIR / "australia"
SARIG_GEOJSON = AU / "sarig" / "petroleum_wells.geojson"
GSQ_DIR = AU / "gsq"
GSQ_WCR_DIR = GSQ_DIR / "wcr"
GSQ_META = GSQ_DIR / "wcr_meta.json"

SARIG_LICENCE = "CC-BY 4.0 (Government of South Australia, Dept. for Energy and Mining — SARIG)"
GSQ_LICENCE = "CC-BY 4.0 (Geological Survey of Queensland — GSQ Open Data Portal)"


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).upper()


# ---------------------------------------------------------------- SARIG (South Australia)
def _sarig_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f not in (0, 0.0) else None  # 0 in this feed means "not recorded", not a real zero


def ingest_sarig(db: Session, wells: dict[str, Well], log=print) -> Counter:
    ws: Counter = Counter()
    if not SARIG_GEOJSON.exists():
        log("au_wells: no SARIG petroleum_wells.geojson — skipped (see data/raw/australia/REPORT.md)")
        return ws
    data = json.loads(SARIG_GEOJSON.read_text())
    fld = Field(name="South Australia petroleum wells (SARIG)", country="Australia", source="sarig")
    db.add(fld)
    db.flush()
    for feat in data["features"]:
        p = feat["properties"]
        name = (p.get("WELL_NAME") or "").strip()
        if not name:
            ws["no_name"] += 1
            continue
        key = _norm(f"AU: {name}")
        if key in wells:
            ws["duplicate"] += 1
            continue
        lon, lat = feat["geometry"]["coordinates"] if feat.get("geometry") else (None, None)
        drillhole_no = p.get("DRILLHOLE_NO")
        w = Well(canonical_name=f"AU: {name}", aliases=[name], field_id=fld.id, field_name=p.get("BASIN") or "South Australia",
                 country="Australia", lat=lat, lon=lon, kb_elev_m=_num(p.get("KB__M")), spud_date=_sarig_date(p.get("SPUDDED")),
                 td_md_m=_num(p.get("TD__M")), status=p.get("STATUS_RIG_RELEASE") or p.get("WELL_TYPE"), well_type=p.get("CLASS"),
                 operator=p.get("OPERATOR"), source="sarig", position_source="SARIG WFS drillholes:petroleum_wells (GDA94, treated as WGS84)",
                 external_id=str(drillhole_no) if drillhole_no is not None else None,
                 fact_url="https://map.sarig.sa.gov.au/")
        db.add(w)
        db.flush()
        wells[key] = w
        ws["sarig_wells"] += 1
    log(f"au_wells sarig: {dict(ws)}")
    return ws


# ---------------------------------------------------------------- GSQ (Queensland) well-completion reports
_PERMIT = re.compile(r"\b(?:PL|ATP)\s*\d+[A-Z]?\b", re.I)
_TITLE_MID = re.compile(r"^(?:(?:PL|ATP)\s*\d+[A-Z]?[,\s]*)+[\s,-]*(.*?)\s*,?\s*WELL\s+(?:COMPLETION|PROPOSAL)\s+REPORT\s*$", re.I)

# best-effort casing / LOT patterns (Australian WCRs vary a lot by decade and operator; only clear,
# unambiguous matches are kept — anything else is left unextracted rather than guessed)
_CASING_RE = re.compile(r'\b(\d{1,2}(?:\s?\d/\d)?)\s*(?:"|in\.?|inch(?:es)?)\s+(?:casing|liner)\b[^.\n]{0,60}?'
                         r'(?:set|run|cemented|shoe)[^.\n]{0,30}?(?:at|@)\s*([\d,]+(?:\.\d+)?)\s*(m|ft)\b', re.I)
_LOT_RE = re.compile(r'\b(LOT|FIT)\b[^.\n]{0,60}?(\d{1,2}\.\d{1,2})\s*(ppg|sg|s\.g\.|lb/gal)\b', re.I)
_LOT_DEPTH_RE = re.compile(r'(?:at|@)\s*([\d,]+(?:\.\d+)?)\s*(m|ft)\b')


def _well_name_from_title(title: str) -> tuple[str, str | None]:
    m = _TITLE_MID.match(title.strip())
    mid = m.group(1).strip(" ,-") if m and m.group(1) else title
    permits = ", ".join(dict.fromkeys(p.upper().replace("  ", " ") for p in _PERMIT.findall(title)))
    return (mid or title).strip(), (permits or None)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_casing_lot(well_id: int, ref: str, full_text: str, ws: Counter):
    """Only a plain 'N in./inch casing set/run/cemented at D m/ft' is trusted; fractional ODs
    ('9 5/8"') are kept in the source ref but not parsed into od_in (no fraction-parsing invented)."""
    for m in _CASING_RE.finditer(full_text):
        od_raw, depth_raw, unit = m.groups()
        od = float(od_raw) if re.fullmatch(r"\d{1,2}(\.\d+)?", od_raw.strip()) else None
        depth = float(depth_raw.replace(",", ""))
        depth_m = depth if unit.lower() == "m" else depth * 0.3048
        ws["casing_rows"] += 1
        yield CasingString(well_id=well_id, casing_type=None, od_in=od, shoe_md_m=depth_m,
                            source_ref=ref)


def _extract_lot(well_id: int, ref: str, full_text: str, ws: Counter):
    lo, hi = cfg()["extract"]["mw_range_ppg"]
    for m in _LOT_RE.finditer(full_text):
        kind, val, unit = m.groups()
        v = float(val)
        ppg = v if unit.lower() in ("ppg", "lb/gal") else sg_to_ppg(v)
        if not (lo <= ppg <= hi):
            continue
        window = full_text[max(0, m.start() - 60):m.start()]
        dm = _LOT_DEPTH_RE.search(window)
        depth_m = None
        if dm:
            dv, du = dm.groups()
            depth_m = float(dv.replace(",", "")) * (1 if du.lower() == "m" else 0.3048)
        yield PressureTest(well_id=well_id, kind="LOT" if kind.upper() == "LOT" else "FIT", md_m=depth_m, emw_ppg=round(ppg, 2),
                            raw_value=v, raw_unit=unit.lower(), casing_shoe_md_m=depth_m, source_ref=ref)
        ws["pressure_tests"] += 1


def ingest_gsq(db: Session, wells: dict[str, Well], log=print) -> Counter:
    ws: Counter = Counter()
    if not GSQ_META.exists() or not GSQ_WCR_DIR.exists():
        log("au_wells: no GSQ wcr_meta.json / wcr/ dir — skipped (see data/raw/australia/REPORT.md)")
        return ws
    meta = json.loads(GSQ_META.read_text())
    fld = Field(name="Queensland petroleum wells (GSQ Open Data Portal)", country="Australia", source="gsq")
    db.add(fld)
    db.flush()
    for m in meta:
        path = GSQ_WCR_DIR / m["filename"]
        if not path.exists():
            ws["file_missing"] += 1
            continue
        title = m.get("title") or m["report_id"]
        well_name, permits = _well_name_from_title(title)
        key = _norm(f"AU: {well_name}")
        w = wells.get(key)
        if w is None:
            aliases = [title, m["report_id"].upper()] + ([permits] if permits else [])
            w = Well(canonical_name=f"AU: {well_name}", aliases=aliases, field_id=fld.id,
                      field_name="Queensland (GSQ)", country="Australia", lat=m.get("lat"), lon=m.get("lon"),
                      spud_date=None, status=None, operator=m.get("owner"), source="gsq",
                      position_source="GSQ Open Data Portal report geometry (GDA2020, treated as WGS84)" if m.get("lat") else None,
                      external_id=m["report_id"].upper(),
                      fact_url=f"https://geoscience.data.qld.gov.au/data/report/{m['report_id']}")
            db.add(w)
            db.flush()
            wells[key] = w
            ws["gsq_wells"] += 1
        try:
            pages, confs = pdf_pages_with_conf(path)
        except Exception as e:  # noqa: BLE001
            log(f"au_wells gsq: cannot read {path.name}: {e}")
            ws["unreadable_pdf"] += 1
            continue
        sha = _sha256(path)
        if db.query(Document).filter(Document.sha256 == sha).first():
            ws["duplicate_doc"] += 1
            continue
        full_text = "\n".join(pages)
        avg_chars = sum(len(t) for t in pages) / max(1, len(pages))
        # scanned = at least one page was read by OCR; its mean word confidence lowers event confidence downstream
        ocr = [c for c in confs if c is not None]
        is_scanned = bool(ocr)
        ocr_conf = round(sum(ocr) / len(ocr), 1) if ocr else None
        no_text = avg_chars < 150  # still near-empty after OCR -> nothing readable
        report_date = None
        if m.get("open_file_date"):
            try:
                report_date = datetime.strptime(m["open_file_date"][:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        doc = Document(well_id=w.id, kind="WCR_PDF", title=title[:250], path=str(path.relative_to(RAW_DIR.parent)),
                       url=f"https://geoscience.data.qld.gov.au/data/report/{m['report_id']}", report_date=report_date,
                       pages=len(pages), is_scanned=is_scanned, ocr_mean_conf=ocr_conf, sha256=sha, licence=GSQ_LICENCE)
        db.add(doc)
        db.flush()
        ws["wcr_docs"] += 1
        if is_scanned:
            ws["ocr_docs"] += 1
        if no_text:
            ws["scanned_no_text"] += 1
        else:
            seq = 0
            seen_pt, seen_cs = set(), set()
            for pi, page in enumerate(pages, start=1):
                for qi, par in enumerate(_paragraphs(page), start=1):
                    for si, s in enumerate(split_sentences(par), start=1):
                        if len(s) < 25:
                            continue
                        seq += 1
                        loc = f"page {pi}, para {qi}" + (f".s{si}" if len(split_sentences(par)) > 1 else "")
                        db.add(Passage(document_id=doc.id, well_id=w.id, locator=loc, seq=seq, text=s[:2000], report_date=report_date))
                        # casing / LOT are read from the same sentence so each row cites an openable page+sentence.
                        # A test is kept only with a depth (the mud window needs one), once per (kind, EMW, depth).
                        ref = f"doc:{doc.id}#{loc}"
                        for cs in _extract_casing_lot(w.id, ref, s, ws):
                            k = (cs.od_in, round(cs.shoe_md_m))
                            if k not in seen_cs:
                                seen_cs.add(k)
                                db.add(cs)
                        for pt in _extract_lot(w.id, ref, s, ws):
                            k = (pt.kind, pt.emw_ppg, round(pt.md_m) if pt.md_m is not None else None)
                            if pt.md_m is not None and k not in seen_pt:
                                seen_pt.add(k)
                                db.add(pt)
                                ws["pressure_tests_kept"] += 1
            ws["passages"] += seq
        db.flush()
    log(f"au_wells gsq: {dict(ws)}")
    return ws


# ---------------------------------------------------------------- entrypoint
def ingest(db: Session, log=print) -> dict:
    wells: dict[str, Well] = {}
    stats: Counter = Counter()
    stats.update(ingest_sarig(db, wells, log))
    stats.update(ingest_gsq(db, wells, log))
    n_sarig = stats.get("sarig_wells", 0)
    n_gsq_docs = stats.get("wcr_docs", 0)
    db.add_all([
        DataSource(name="SARIG (SA) — petroleum wells WFS layer", url="https://services.sarig.sa.gov.au/vector/drillholes/wfs",
                   licence=SARIG_LICENCE, records=n_sarig, notes="live GeoServer WFS, downloaded whole; no well-level reports (SA report PDFs sit behind a per-well request form)"),
        DataSource(name="GSQ Open Data Portal — Queensland well completion reports", url="https://geoscience.data.qld.gov.au/",
                   licence=GSQ_LICENCE, records=n_gsq_docs, notes="sample of petroleum/oil WCR PDFs (CSG excluded); bulk QPED database export needs an emailed-link queue, not used"),
    ])
    db.flush()
    log(f"au_wells: {dict(stats)}")
    return dict(stats)
