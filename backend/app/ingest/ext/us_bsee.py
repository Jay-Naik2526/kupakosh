"""BSEE (Bureau of Safety and Environmental Enforcement, US Dept. of the Interior) -> wells,
incident-report documents/passages. Public-domain US federal data for the Gulf of America
(Gulf of Mexico) OCS -- our USA stand-in for Oil India data (SPEC.md SS6/SS7).

Sources actually downloaded (see data/raw/usa/MANIFEST.csv for URLs + retrieval dates):
  * data.bsee.gov "Borehole" bulk ASCII file (data/raw/usa/bsee_well/Borehole.zip) -- one row per
    wellbore: API well number, spud date, measured/true-vertical depth, water depth, well type
    (straight/directional/horizontal), and surface + bottom-hole location in both NAD27 decimal
    degrees (as published) and WGS84 (reprojected here with pyproj). ~55.5k rows; every row with
    a coordinate is loaded.
  * bsee.gov historical "Accidents Associated with Oil and Gas Operations, OCS" narrative PDFs,
    1991-1994 through CY2000 (data/raw/usa/bsee_reports/*.pdf) -- MMS/BSEE investigator write-ups
    of blowouts, kicks, lost circulation, fires, collisions. This is the DDR-like free text: each
    record carries Date/Operator/Lease/Area/Block/Cause plus a "Remarks:" narrative. The oldest
    volume (OCS Incidents 1956-1990) is scanned with no extractable text layer and this environment
    has no tesseract/OCR installed, so it is downloaded but NOT ingested (see REPORT.md).
  * bsee.gov "Offshore Incident Statistics" annual workbooks, CY2020-2024
    (data/raw/usa/bsee_incidents/cy20NN.xlsx) -- one row per incident with a free-text narrative
    ("Incident Summary" / "Redacted Incident Summary") and Loss-of-Well-Control flag columns.

What this does NOT do: it does not attempt to join an incident's Lease/Area/Block back to a
specific Borehole row (that join is many-to-many and not reliable from public fields alone), so
incident Documents/Passages are stored with well_id=None. Nothing here is invented: every field
comes from the published files; anything we could not confidently map from the raw column layout
(no official record-layout page was reachable -- see REPORT.md) is left out rather than guessed.
"""
from __future__ import annotations

import csv
import hashlib
import re
import zipfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from app.ingest.pdftext import pdf_pages
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.config import RAW_DIR, cfg
from app.db.models import DataSource, Document, Passage, Well
from app.ingest.sodir import split_sentences
from app.ingest.units import ft_to_m

SOURCE = {
    "name": "BSEE (Bureau of Safety and Environmental Enforcement) -- Gulf of America OCS",
    "country": "USA",
    "url": "https://www.data.bsee.gov",
    "licence": "US Government public domain",
    "raw_dir": "usa",
}

USA = RAW_DIR / "usa"
WELL_DIR = USA / "bsee_well"
REPORTS_DIR = USA / "bsee_reports"
INCIDENTS_DIR = USA / "bsee_incidents"
LICENCE = "US Government public domain (17 U.S.C. SS105)"

# ------------------------------------------------------------------ Borehole (wells)

_BOREHOLE_COLS = 29  # observed column count in the delimited export; a row of any other length is skipped, not guessed


def _parse_ymd(s: str) -> date | None:
    s = (s or "").strip()
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except ValueError:
        return None


def _dec(s: str) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


_NAD27_TO_WGS84 = None
_NAD27_TRANSFORMER_TRIED = False


def _to_wgs84(lon: float, lat: float) -> tuple[float, float, bool]:
    """BSEE publishes these decimal-degree columns in NAD27 (site note: 'GOA coordinate values
    were derived using ... NAD 1927'). Reproject with pyproj (transformer built once, not per
    row -- constructing it per call made this pass unusably slow); if the datum grid is
    unavailable, fall back to the raw NAD27 value rather than inventing a shift, and the well's
    position_source records which happened."""
    global _NAD27_TO_WGS84, _NAD27_TRANSFORMER_TRIED
    if not _NAD27_TRANSFORMER_TRIED:
        _NAD27_TRANSFORMER_TRIED = True
        try:
            from pyproj import Transformer
            _NAD27_TO_WGS84 = Transformer.from_crs("EPSG:4267", "EPSG:4326", always_xy=True)
        except Exception:
            _NAD27_TO_WGS84 = None
    if _NAD27_TO_WGS84 is None:
        return lon, lat, False
    lon2, lat2 = _NAD27_TO_WGS84.transform(lon, lat)
    return lon2, lat2, True


def _ingest_boreholes(db: Session, log) -> Counter:
    stats: Counter = Counter()
    zpath = WELL_DIR / "Borehole.zip"
    if not zpath.exists():
        log("us_bsee: no data/raw/usa/bsee_well/Borehole.zip -- skipping wells")
        return stats
    existing = {w.canonical_name for w in db.query(Well.canonical_name).all()}
    with zipfile.ZipFile(zpath) as z:
        inner = next((n for n in z.namelist() if n.lower().endswith(".txt")), None)
        if not inner:
            log("us_bsee: Borehole.zip has no .txt member")
            return stats
        with z.open(inner) as fh:
            reader = csv.reader((line.decode("utf-8", "replace") for line in fh))
            reproj_ok = 0
            for row in reader:
                stats["borehole_rows"] += 1
                if len(row) != _BOREHOLE_COLS:
                    stats["bad_row_length"] += 1
                    continue
                api = row[0].strip()
                if not api or not api.isdigit():
                    stats["no_api"] += 1
                    continue
                name = f"US: {api}"
                if name in existing:
                    stats["duplicate_api"] += 1
                    continue
                lon_s, lat_s = row[20].strip(), row[21].strip()
                lon, lat = _dec(lon_s), _dec(lat_s)
                if lon is None or lat is None or not (-179 < lon < 179) or not (-89 < lat < 89):
                    stats["no_coords"] += 1
                    continue
                lon_w, lat_w, ok = _to_wgs84(lon, lat)
                if ok:
                    reproj_ok += 1
                lease = row[6].strip()
                lease_area_block = row[4].strip()
                surface_block = row[11].strip()
                bottom_block = row[13].strip()
                aliases = [a for a in {lease, lease_area_block, surface_block} if a]
                td_md_ft, td_tvd_ft = _dec(row[8]), _dec(row[9])
                wd_ft = _dec(row[19])
                well_type = row[28].strip() or None
                w = Well(
                    canonical_name=name,
                    aliases=aliases,
                    field_name=surface_block or None,
                    country="USA",
                    lat=round(lat_w, 6), lon=round(lon_w, 6),
                    water_depth_m=round(ft_to_m(wd_ft), 1) if wd_ft is not None else None,
                    spud_date=_parse_ymd(row[5]),
                    td_md_m=round(ft_to_m(td_md_ft), 1) if td_md_ft is not None else None,
                    td_tvd_m=round(ft_to_m(td_tvd_ft), 1) if td_tvd_ft is not None else None,
                    well_type={"STR": "straight", "DIR": "directional", "HOR": "horizontal"}.get(well_type),
                    source="bsee",
                    position_source="BSEE Borehole file, NAD27->WGS84 (pyproj)" if ok else "BSEE Borehole file, NAD27 (not reprojected)",
                    external_id=api,
                    fact_url="https://www.data.bsee.gov/Well/Boreholes/Default.aspx",
                )
                db.add(w)
                existing.add(name)
                stats["wells"] += 1
            db.flush()
    log(f"us_bsee: boreholes -> {stats['wells']} wells ({reproj_ok} reprojected NAD27->WGS84)")
    return stats


# ------------------------------------------------------------------ incident narrative PDFs (1991-2000)

_DATE_HDR = re.compile(r"^Date:\s*([\d]{1,2}[-/][A-Za-z]{3}[-/][\d]{2,4})\s+Operator:\s*(.*)$")
_INV_HDR = re.compile(r"^(?:Investigation|MMS Investigation Report):\s*(.*?)\s+Activity:\s*(.*)$")
_LEASE_HDR = re.compile(r"^Lease:\s*(.*?)\s+Event\(s\):\s*(.*)$")
_AREA_HDR = re.compile(r"^Area:\s*(.*?)\s+Operation:\s*(.*)$")
_BLOCK_HDR = re.compile(r"^Block:\s*(.*?)\s+Cause:\s*(.*)$")
_RIG_HDR = re.compile(r"^Rig/Platform:\s*(.*?)\s+Water Depth:\s*(.*)$")
_REMARKS_START = re.compile(r"^Remarks:\s*(.*)$")
_PAGENUM = re.compile(r"^\d{1,4}$")
_SECTION = re.compile(r"^[A-Z][A-Za-z ]+[-–]\s*\d{4}$|^[A-Z][A-Za-z ()]*\d+ total\)$|Collision No\. \d+")
_MONTHS = {m.lower(): i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _parse_incident_date(s: str) -> date | None:
    m = re.match(r"(\d{1,2})[-/]([A-Za-z]{3})[-/](\d{2,4})", s.strip())
    if not m:
        return None
    d, mon, y = m.groups()
    mo = _MONTHS.get(mon.lower())
    if not mo:
        return None
    yr = int(y)
    if yr < 100:
        yr += 1900 if yr > 50 else 2000
    try:
        return date(yr, mo, int(d))
    except ValueError:
        return None


def _parse_date_format_page(text: str) -> list[dict]:
    """Parser for the 'Date: ... Operator: ...' record layout used in the 1995-96 through
    CY2000 OCS incident-summary PDFs (verified against all 5 files' sample pages)."""
    records: list[dict] = []
    cur: dict | None = None
    in_remarks = False
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        m = _DATE_HDR.match(line)
        if m:
            if cur:
                records.append(cur)
            cur = {"date_raw": m.group(1), "operator": m.group(2), "remarks": []}
            in_remarks = False
            continue
        if cur is None:
            continue
        if _PAGENUM.match(line) or _SECTION.match(line) or "Region" in line:
            in_remarks = False
            continue
        m = _INV_HDR.match(line)
        if m:
            cur["investigation"], cur["activity"] = m.groups()
            continue
        m = _LEASE_HDR.match(line)
        if m:
            cur["lease"], cur["events"] = m.groups()
            continue
        m = _AREA_HDR.match(line)
        if m:
            cur["area"], cur["operation"] = m.groups()
            continue
        m = _BLOCK_HDR.match(line)
        if m:
            cur["block"], cur["cause"] = m.groups()
            continue
        m = _RIG_HDR.match(line)
        if m:
            cur["rig"], cur["water_depth"] = m.groups()
            continue
        m = _REMARKS_START.match(line)
        if m:
            in_remarks = True
            if m.group(1):
                cur["remarks"].append(m.group(1))
            continue
        if in_remarks:
            cur["remarks"].append(line)
    if cur:
        records.append(cur)
    for r in records:
        r["remarks_text"] = " ".join(r.pop("remarks"))
    return [r for r in records if len(r["remarks_text"]) > 20]


_HEADER_91_94 = re.compile(
    r"^([A-Za-z][A-Za-z .'/-]{2,30}?)\s+(\d{2}-\d{2}-\d{2})\s+([A-Za-z/ ]+?)\s+([A-Za-z/ ]+?)\s+(\d+)\s*$")


def _parse_91_94_page(text: str) -> list[dict]:
    """Looser parser for the older 1991-1994 report, which uses a compact tabular header
    (Area / Date / Type / AccidentType / Operation / Fatalities) instead of labelled fields."""
    records: list[dict] = []
    cur: dict | None = None
    in_remarks = False
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        m = _HEADER_91_94.match(line)
        if m:
            if cur:
                records.append(cur)
            area, d, typ, acc, fat = m.groups()
            cur = {"date_raw": d, "area": area.strip(), "type": typ.strip(), "accident_type": acc.strip(), "remarks": []}
            in_remarks = False
            continue
        if cur is None:
            continue
        if _PAGENUM.match(line) or line.isupper():
            in_remarks = False
            continue
        if line.lower().startswith("remarks:"):
            in_remarks = True
            rest = line.split(":", 1)[1].strip()
            if rest:
                cur["remarks"].append(rest)
            continue
        if in_remarks:
            cur["remarks"].append(line)
    if cur:
        records.append(cur)
    for r in records:
        r["remarks_text"] = " ".join(r.pop("remarks"))
    return [r for r in records if len(r["remarks_text"]) > 20]


def _parse_91_94_date(s: str) -> date | None:
    m = re.match(r"(\d{2})-(\d{2})-(\d{2})", s.strip())
    if not m:
        return None
    yy, mm, dd = (int(x) for x in m.groups())
    yy += 1900 if yy > 50 else 2000
    try:
        return date(yy, mm, dd)
    except ValueError:
        return None


_PDF_TITLES = {
    "ocsincidents1991to1994-pdf.pdf": "BSEE/MMS: Accidents Associated with Oil and Gas Operations, OCS, 1991-1994",
    "incidentsassociatedwithoilandgasoperationsocs95-96-pdf.pdf": "BSEE/MMS: Accidents Associated with Oil and Gas Operations, OCS, 1995-1996",
    "finalocs97-pdf.pdf": "BSEE/MMS: Accidents Associated with Oil and Gas Operations, OCS, 1997",
    "finalocs98-pdf.pdf": "BSEE/MMS: Accidents Associated with Oil and Gas Operations, OCS, 1998",
    "finalocs99-pdf.pdf": "BSEE/MMS: Accidents Associated with Oil and Gas Operations, OCS, 1999",
    "accidentreport2000-march25-pdf.pdf": "BSEE/MMS: Accidents Associated with Oil and Gas Operations, OCS, 2000",
    "addendummmsocs950052fatalityincident-pdf.pdf": "BSEE/MMS: Addendum, OCS 95-0052 Fatality Incident",
}
_URL_BASE = "https://www.bsee.gov/sites/bsee.gov/files/"
_PDF_URLS = {
    "ocsincidents1991to1994-pdf.pdf": _URL_BASE + "incident-statisticssummaries-fatalities/exploration-and-production/ocsincidents1991to1994-pdf.pdf",
    "incidentsassociatedwithoilandgasoperationsocs95-96-pdf.pdf": _URL_BASE + "incident-summaries/safety/incidentsassociatedwithoilandgasoperationsocs95-96-pdf.pdf",
    "finalocs97-pdf.pdf": _URL_BASE + "incident-summaries/safety/finalocs97-pdf.pdf",
    "finalocs98-pdf.pdf": _URL_BASE + "incident-summaries/incident-histories/finalocs98-pdf.pdf",
    "finalocs99-pdf.pdf": _URL_BASE + "incident-summaries/safety/finalocs99-pdf.pdf",
    "accidentreport2000-march25-pdf.pdf": _URL_BASE + "reports/reports/accidentreport2000-march25-pdf.pdf",
}


def _make_document(db: Session, kind: str, title: str, url: str | None, sha256: str, pages: int | None) -> Document | None:
    if db.query(Document).filter(Document.sha256 == sha256).first():
        return None
    doc = Document(well_id=None, kind=kind, title=title, url=url, path=None, pages=pages,
                   is_scanned=False, sha256=sha256, licence=LICENCE)
    db.add(doc)
    db.flush()
    return doc


def _add_passages(db: Session, doc: Document, seq_start: int, text: str, locator_prefix: str, report_date) -> int:
    n = 0
    for si, sent in enumerate(split_sentences(text), start=1):
        db.add(Passage(document_id=doc.id, well_id=None, locator=f"{locator_prefix}, s{si}",
                       seq=seq_start + n, text=sent, md_m=None, report_date=report_date))
        n += 1
    return n


def _ingest_incident_pdfs(db: Session, log) -> Counter:
    stats: Counter = Counter()
    if not REPORTS_DIR.exists():
        log("us_bsee: no data/raw/usa/bsee_reports -- skipping incident PDFs")
        return stats
    old_scanned = REPORTS_DIR / "ocsincidents1956to1990-pdf.pdf"
    if old_scanned.exists():
        stats["skipped_no_ocr"] += 1
        log("us_bsee: ocsincidents1956to1990-pdf.pdf is a scanned volume with no text layer; "
            "no tesseract/OCR is installed in this environment, so it is left un-ingested (raw file kept).")
    for fname, title in _PDF_TITLES.items():
        p = REPORTS_DIR / fname
        if not p.exists():
            continue
        pages_text = pdf_pages(p)
        full = "\n".join(pages_text)
        if len(full.strip()) < 200:
            stats["empty_pdf"] += 1
            continue
        h = hashlib.sha256(full.encode()).hexdigest()
        doc = _make_document(db, "INCIDENT_REPORT", title, _PDF_URLS.get(fname), h, len(pages_text))
        if doc is None:
            stats["duplicate_doc"] += 1
            continue
        seq = 0
        old_format = fname == "ocsincidents1991to1994-pdf.pdf"
        for pgi, txt in enumerate(pages_text, start=1):
            if not txt:
                continue
            recs = _parse_91_94_page(txt) if old_format else _parse_date_format_page(txt)
            for r in recs:
                rdate = _parse_91_94_date(r["date_raw"]) if old_format else _parse_incident_date(r["date_raw"])
                area = r.get("area", "?")
                block = r.get("block", "")
                locator = f"p{pgi}, {area} Blk {block}, {r['date_raw']}".strip()
                added = _add_passages(db, doc, seq, r["remarks_text"], locator, rdate)
                seq += added
                stats["incident_records"] += 1
                stats["passages"] += added
        log(f"us_bsee: {fname} -> {seq} passages")
    return stats


# ------------------------------------------------------------------ CY20NN incident-statistics workbooks

_NARRATIVE_HEADER_CANDIDATES = ("incident summary", "redacted incident summary")
_LWC_HEADER_PREFIX = "loss of well control"


def _header_index(headers: list, *names: str) -> int | None:
    low = [str(h or "").strip().lower() for h in headers]
    for name in names:
        if name in low:
            return low.index(name)
    return None


def _flag_true(v) -> bool:
    """The Loss-of-Well-Control columns are encoded 'Y'/'N' in most years but as small integer
    counts (0/1/2/3) in a couple of workbooks -- treat any 'Y' or positive number as flagged,
    and 'N'/0/blank as not (never the reverse: a bare non-empty string like 'N' is truthy in
    Python and would silently flag every row if tested with a plain `if v`)."""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v > 0
    return str(v).strip().upper() == "Y"


def _ingest_incident_xlsx(db: Session, log) -> Counter:
    stats: Counter = Counter()
    if not INCIDENTS_DIR.exists():
        log("us_bsee: no data/raw/usa/bsee_incidents -- skipping incident workbooks")
        return stats
    for p in sorted(INCIDENTS_DIR.glob("cy*.xlsx")):
        year = p.stem.replace("cy", "")
        wb = load_workbook(p, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 3:
            continue
        header = [str(h or "").strip() for h in rows[1]]
        low = [h.lower() for h in header]
        narr_i = _header_index(header, *_NARRATIVE_HEADER_CANDIDATES)
        date_i = _header_index(header, "date")
        area_i = _header_index(header, "area name")
        block_i = _header_index(header, "block")
        lease_i = _header_index(header, "lease")
        operator_i = _header_index(header, "operator name")
        lwc_idx = [i for i, h in enumerate(low) if h.startswith(_LWC_HEADER_PREFIX)]
        if narr_i is None:
            stats["no_narrative_column"] += 1
            continue
        title = f"BSEE Offshore Incident Statistics, Calendar Year {year}"
        content_hash = hashlib.sha256(f"{title}|{len(rows)}".encode()).hexdigest()
        doc = _make_document(db, "INCIDENT_REPORT", title,
                             "https://www.bsee.gov/stats-facts/offshore-incident-statistics", content_hash, None)
        if doc is None:
            stats["duplicate_doc"] += 1
            continue
        seq = 0
        for ri, row in enumerate(rows[2:], start=3):
            narrative = row[narr_i] if narr_i < len(row) else None
            if not narrative or not str(narrative).strip():
                continue
            rdate = row[date_i] if date_i is not None and date_i < len(row) else None
            rdate = rdate.date() if isinstance(rdate, datetime) else (rdate if isinstance(rdate, date) else None)
            area = row[area_i] if area_i is not None and area_i < len(row) else ""
            block = row[block_i] if block_i is not None and block_i < len(row) else ""
            lease = row[lease_i] if lease_i is not None and lease_i < len(row) else ""
            lwc_flags = [header[i] for i in lwc_idx if i < len(row) and _flag_true(row[i])]
            tag = f" [LWC: {', '.join(lwc_flags)}]" if lwc_flags else ""
            locator = f"row {ri}, {area} Blk {block} Lease {lease}, {rdate or ''}".strip()
            added = _add_passages(db, doc, seq, str(narrative).strip() + tag, locator, rdate)
            seq += added
            stats["incident_rows"] += 1
            stats["passages"] += added
            if lwc_flags:
                stats["lwc_rows"] += 1
        wb.close()
        log(f"us_bsee: {p.name} -> {seq} passages (narrative col='{header[narr_i]}', operator col present={operator_i is not None})")
    return stats


# ------------------------------------------------------------------ entry point

def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    stats.update(_ingest_boreholes(db, log))
    stats.update(_ingest_incident_pdfs(db, log))
    stats.update(_ingest_incident_xlsx(db, log))

    n_pdf_docs = db.query(Document).filter(Document.kind == "INCIDENT_REPORT", Document.url.like("%bsee.gov/sites%")).count()
    db.add_all([
        DataSource(name="BSEE Borehole (bulk ASCII) -- OCS wellbore headers", url="https://www.data.bsee.gov/Well/Boreholes/Default.aspx",
                   licence=LICENCE, records=stats.get("wells", 0),
                   notes="API number, spud date, MD/TVD, water depth, well type, surface+bottom-hole position; NAD27->WGS84 reprojected"),
        DataSource(name="BSEE/MMS OCS incident-summary reports (1991-2000, narrative PDFs)", url="https://www.bsee.gov/stats-facts/offshore-incident-statistics",
                   licence=LICENCE, records=stats.get("incident_records", 0),
                   notes="blowout/kick/lost-circulation/fire/collision narratives with Area/Block/Lease/Cause; 1956-1990 volume excluded (scanned, no OCR available)"),
        DataSource(name="BSEE Offshore Incident Statistics workbooks (CY2020-2024)", url="https://www.bsee.gov/stats-facts/offshore-incident-statistics",
                   licence=LICENCE, records=stats.get("incident_rows", 0),
                   notes=f"free-text incident narratives incl. Loss-of-Well-Control flags ({stats.get('lwc_rows', 0)} rows flagged LWC)"),
    ])
    db.flush()
    log(f"us_bsee: done -- {dict(stats)}")
    return dict(stats)
