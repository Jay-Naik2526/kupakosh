"""NLOG (Nederlands Olie- en Gasportaal / Dutch subsurface data portal, run by TNO for the Ministry
of Economic Affairs and Climate) -> Dutch wells, formation tops, and public well-report PDFs.

Sources (all public, no login):
  * https://www.nlog.nl/nlog-mapviewer/rest/brh/boreholes  (POST {}) -> borehole headers for all
    6,737 Dutch onshore + offshore boreholes (operator, dates, TD, status, purpose, result).
  * https://www.nlog.nl/nlog-mapviewer/rest/brh/details    (POST [boreholeDbk, ...]) -> per-well detail
    incl. WGS84 lat/lon, RD/UTM31 coordinates, field, rig, KB height.
  * https://www.nlog.nl/nlog-mapviewer/rest/brh/documents  (POST boreholeDbk) -> per-well document list
    (title, asset type, file type, size, download id). PDFs are fetched from
    https://www.nlog.nl/brh-web/rest/brh/document/{assetBfileDbk} (no auth).
  * data/raw/netherlands/nlog/nlog_stratstelsel.csv: the NLOG bulk "thematische data boringen" download
    (https://www.nlog.nl/sites/default/files/2026-09/thematische_data_boringen.zip), lithostratigraphy
    per wellbore interval (formation name, top/base along-hole depth, coordinates in RD/UTM31/WGS84).

These REST endpoints are the same ones the public NLOG Datacenter web app (nlog.nl/datacenter) calls
from the browser; they require no API key and return plain JSON. Discovered by inspecting the app's
network traffic (see data/raw/netherlands/REPORT.md).

Licence: NLOG data and reports are Dutch government open data (TNO / Ministry of EZK), citable and
downloadable without registration — see https://www.nlog.nl/en/disclaimer. We record this licence text
verbatim per DataSource/Document row; nothing here is redistributed beyond what NLOG itself serves.

What we do NOT invent: operator, status, spud/end date, and TD come only from the boreholes/details
JSON; formation tops only from the stratstelsel CSV; report text only from the downloaded PDFs. Wells
with no coordinate in the details response are skipped for geometry (none observed in practice — all
6,737 records carry latitudeWgs84/longitudeWgs84). Casing/LOT rows are NOT created here: NLOG's bulk
export does not carry them in a form we can cite reliably, and the sampled report PDFs did not expose a
clean casing/cement table (see REPORT.md); adding guessed rows would violate SPEC.md's "invent
nothing" rule.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from app.ingest.pdftext import pdf_pages
from sqlalchemy.orm import Session

from app.config import RAW_DIR
from app.db.models import DataSource, Document, FormationTop, Passage, Well
from app.ingest.india_docs import _paragraphs
from app.ingest.sodir import split_sentences

NL = RAW_DIR / "netherlands" / "nlog"
LICENCE = "Dutch government open data (TNO / Ministry of Economic Affairs and Climate, NLOG) — public, no registration"
MAPVIEWER_URL = "https://www.nlog.nl/nlog-mapviewer/brh/{dbk}"
DOCUMENT_URL = "https://www.nlog.nl/brh-web/rest/brh/document/{bfile}"

SOURCE = {
    "name": "NLOG (Netherlands, TNO/EZK)",
    "country": "Netherlands",
    "url": "https://www.nlog.nl/en/boreholes",
    "licence": LICENCE,
    "raw_dir": "netherlands",
}

# report-type document titles worth extracting as citable text (end-of-well / final well / geological
# summary reports); excludes raw logs, surveys, and petrophysical curve dumps which carry no drilling narrative
_REPORT_TITLE = re.compile(
    r"(?i)\b(final well report|end of well report|geological (?:final )?well report|"
    r"final wellsite geological report|final well ?site geological report|well summary|"
    r"geological well summary|daily geological report|daily drilling report|drilling report|geosummary)\b"
)


def _epoch_ms_to_date(ms) -> date | None:
    if not ms:
        return None
    try:
        return datetime.utcfromtimestamp(ms / 1000).date()
    except (ValueError, OSError, OverflowError):
        return None


def _num_nl(s: str | None) -> float | None:
    """NLOG CSV numbers use a comma decimal separator, e.g. '1256,26'."""
    if s is None or s == "":
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _level(name: str) -> str:
    n = name.lower()
    if "group" in n or "groep" in n:
        return "GROUP"
    if "member" in n:
        return "MEMBER"
    return "FORMATION"


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()

    headers_p = NL / "nlog_boreholes_headers.json"
    details_p = NL / "nlog_boreholes_details.json"
    strat_p = NL / "nlog_stratstelsel.csv"
    if not headers_p.exists() or not details_p.exists():
        log("nl_nlog: no data/raw/netherlands/nlog/nlog_boreholes_*.json — nothing to ingest")
        return {}

    headers = {h["boreholeDbk"]: h for h in json.loads(headers_p.read_text())}
    details = json.loads(details_p.read_text())

    wells: dict[str, Well] = {}
    wells_by_nitg: dict[str, Well] = {}
    dbk_to_well: dict[int, Well] = {}
    for d in details:
        dbk = d.get("boreholeDbk")
        h = headers.get(dbk, {})
        name = (d.get("boreholeName") or h.get("boreholeName") or "").strip()
        if not name:
            stats["details_no_name"] += 1
            continue
        canon = f"NL: {name}"
        if canon in wells:
            continue
        lat, lon = d.get("latitudeWgs84"), d.get("longitudeWgs84")
        field_name = d.get("fieldName") or (f"Block {d.get('blockCd')}" if d.get("blockCd") else None)
        w = Well(
            canonical_name=canon,
            aliases=[name] + ([d["shortName"]] if d.get("shortName") and d["shortName"] != name else []),
            field_id=None, field_name=field_name, country="Netherlands",
            lat=lat, lon=lon,
            kb_elev_m=d.get("drpHeightInMeters"),
            water_depth_m=None,
            spud_date=_epoch_ms_to_date(h.get("startDate") or d.get("startDate")),
            td_md_m=h.get("endAhDepthInMeters") or d.get("endAhDepthInMeters"),
            td_tvd_m=h.get("tvdInMeters") or d.get("tvdInMeters"),
            status=h.get("statusDescription") or d.get("statusDescription"),
            purpose=d.get("purposeDescription") or h.get("purposeCd"),
            well_type="offshore" if (h.get("onOffshore") or d.get("onOffshore")) == "OFF" else "onshore",
            operator=h.get("clientOrgName") or d.get("clientOrgName"),
            formation_at_td=None,
            source="nlog",
            position_source="nlog brh/details (WGS84)" if lat is not None else None,
            parent_well=None,
            external_id=d.get("nitgNr") or d.get("uwi") or str(dbk),
            fact_url=MAPVIEWER_URL.format(dbk=dbk),
        )
        db.add(w)
        wells[canon] = w
        dbk_to_well[dbk] = w
        if d.get("nitgNr"):
            wells_by_nitg[d["nitgNr"]] = w
        stats["wells"] += 1
    db.flush()
    log(f"nl_nlog: {stats['wells']} wells from {len(details)} NLOG borehole detail records")

    # ---- formation tops (lithostratigraphy) ----
    top_rows: list[FormationTop] = []
    if strat_p.exists():
        with open(strat_p, encoding="latin-1", newline="") as f:
            reader = csv.DictReader(f, delimiter=";", quotechar='"')
            for r in reader:
                well_name = (r.get("WELLBORE") or "").strip()
                # join by NITG_NR (the stable NLOG well identifier): well-name spellings differ between
                # this bulk export and the brh/details API for sidetracks (e.g. "-S1" vs "-SIDETRACK1")
                w = wells_by_nitg.get((r.get("NITG_NR") or "").strip()) or wells.get(f"NL: {well_name}")
                if not w:
                    stats["tops_no_well"] += 1
                    continue
                formation = (r.get("STRAT_UNIT_NM") or "").strip()
                if not formation or formation.upper() == "NOT INTERPRETED":
                    continue
                top_ah = _num_nl(r.get("TOP_AH"))
                base_ah = _num_nl(r.get("BOTTOM_AH"))
                tv_top_nap = _num_nl(r.get("TV_TOP_NAP"))
                # NLOG reports TVD relative to NAP (mean sea level datum); convert to TVD-from-KB using
                # the well's own KB height so it is comparable with every other source in this schema.
                top_tvd = (tv_top_nap + w.kb_elev_m) if (tv_top_nap is not None and w.kb_elev_m is not None) else None
                top_rows.append(FormationTop(
                    well_id=w.id, formation=formation, level=_level(formation), grp=None,
                    lithology=None, top_md_m=top_ah, top_tvd_m=top_tvd, base_md_m=base_ah,
                    source="nlog",
                    source_ref=f"nlog:stratstelsel:{well_name}#{r.get('STRAT_UNIT_CD')}:{r.get('TOP_AH')}-{r.get('BOTTOM_AH')}m",
                ))
    else:
        log("nl_nlog: no nlog_stratstelsel.csv — skipping formation tops")
    db.add_all(top_rows)
    db.flush()
    stats["formation_tops"] = len(top_rows)
    log(f"nl_nlog: {len(top_rows)} formation-top rows")

    # ---- report PDFs -> documents + passages ----
    reports_dir = NL / "reports"
    # report filenames are "<sanitised boreholeName>__<assetBfileDbk>.pdf" (see download_reports() /
    # REPORT.md); match by applying the same sanitisation to every known well name rather than guessing
    # the inverse (apostrophes and spaces both collapse to "_", so the mapping is not reversible)
    sanitised_to_well = {re.sub(r"[^A-Za-z0-9_.-]+", "_", name[4:]): w for name, w in wells.items()}
    selected_p = NL / "selected_reports.json"
    title_by_bfile: dict[int, str] = {}
    if selected_p.exists():
        for s in json.loads(selected_p.read_text()):
            title_by_bfile[s["assetBfileDbk"]] = s["fullTitle"]
    n_docs = n_pages = n_passages = n_scanned = 0
    if reports_dir.exists():
        for pdf_path in sorted(reports_dir.glob("*.pdf")):
            sanitised_name, bfile_str = pdf_path.stem.rsplit("__", 1)
            w = sanitised_to_well.get(sanitised_name)
            bfile = int(bfile_str) if bfile_str.isdigit() else None
            full_title = title_by_bfile.get(bfile) or sanitised_name.replace("_", " ")
            raw_bytes = pdf_path.read_bytes()
            sha = hashlib.sha256(raw_bytes).hexdigest()
            if db.query(Document).filter(Document.sha256 == sha).first():
                stats["duplicate_docs"] += 1
                continue
            try:
                pages = pdf_pages(pdf_path)
            except Exception as e:  # noqa: BLE001 - corrupt/unreadable PDF must not stop the whole run
                stats["unreadable_pdf"] += 1
                log(f"nl_nlog: could not read {pdf_path.name}: {e!r}")
                continue
            text_len = sum(len(p) for p in pages)
            is_scanned = text_len < 200
            title_lower = full_title.lower()
            kind = ("EOWR_PDF" if ("final well report" in title_lower or "end of well" in title_lower
                                    or "geological well summary" in title_lower or "geosummary" in title_lower
                                    or "well summary" in title_lower)
                    else "DDR_PDF" if ("daily" in title_lower or "drilling report" in title_lower)
                    else "WCR_PDF" if "completion" in title_lower
                    else "OTHER")
            doc = Document(
                well_id=w.id if w else None, kind=kind, title=f"NLOG report — {sanitised_name.replace('_', ' ')} — {full_title}",
                path=str(pdf_path.relative_to(RAW_DIR.parent)),
                url=DOCUMENT_URL.format(bfile=bfile) if bfile else None, report_date=None,
                pages=len(pages), is_scanned=is_scanned, ocr_mean_conf=None, sha256=sha, licence=LICENCE,
            )
            db.add(doc)
            db.flush()
            n_docs += 1
            n_pages += len(pages)
            if is_scanned:
                n_scanned += 1
                continue
            seq = 0
            for pi, page in enumerate(pages, start=1):
                for qi, para in enumerate(_paragraphs(page), start=1):
                    for si, sent in enumerate(split_sentences(para), start=1):
                        if len(sent) < 20:
                            continue
                        seq += 1
                        db.add(Passage(document_id=doc.id, well_id=w.id if w else None,
                                       locator=f"page {pi}, para {qi}.s{si}", seq=seq, text=sent[:2000]))
            n_passages += seq
            db.flush()
    else:
        log("nl_nlog: no data/raw/netherlands/nlog/reports/ — no report PDFs ingested")
    stats["report_documents"] = n_docs
    stats["report_pages"] = n_pages
    stats["report_passages"] = n_passages
    stats["report_documents_scanned"] = n_scanned
    log(f"nl_nlog: {n_docs} report PDFs ({n_scanned} scanned/no text), {n_passages} passages")

    db.add(DataSource(
        name="NLOG — Dutch borehole headers, lithostratigraphy, and public well-report PDFs",
        url="https://www.nlog.nl/en/boreholes",
        licence=LICENCE,
        records=stats["wells"] + stats["formation_tops"] + n_docs,
        notes=(f"{stats['wells']} boreholes (of 6,737 NLOG records), {stats['formation_tops']} formation-top rows, "
               f"{n_docs} sampled public well-report PDFs ({n_scanned} scanned/no extractable text). "
               "Real Dutch public data (TNO/EZK), used as a geographic stand-in, not Oil India data."),
    ))
    db.flush()
    log(f"nl_nlog: {dict(stats)}")
    return dict(stats)
