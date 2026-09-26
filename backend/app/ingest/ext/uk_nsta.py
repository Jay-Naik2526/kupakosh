"""United Kingdom (NSTA / North Sea Transition Authority Open Data) -> wells, formation tops, documents.

Sources (downloaded to data/raw/uk/nsta/, see data/raw/uk/MANIFEST.csv):
  * "UKCS offshore wellbore top holes (WGS84)" ArcGIS feature layer (13,382 wellbores): well header
    (registration no., coordinates, spud/TD/completion dates, TD depth, operator, field, status,
    water depth). Field TOPHOLEDTM records the *actual* horizontal datum of the decimal-degree
    coordinates (mostly ED50, despite the "WGS84" service name), so ED50 points are reprojected to
    WGS84 with pyproj; WGS84/ETRS89 points are used as-is; anything else is left uncoordinated.
  * "UKCS offshore petroleum wells with linked reports (WGS84)" (953 wells): each row links up to
    6 public legacy report PDFs (mostly Shell legacy geochemistry investigations of oil/gas samples
    from named wells) hosted on the NSTA's own blob storage. A capped sample of these PDFs is
    downloaded (data/raw/uk/nsta/reports/, see reports_manifest.json) and turned into citable
    Document + Passage rows.
  * "UKCS offshore petroleum exploration & appraisal well results (ED50)" (110 wells): target/
    reservoir name, age, rock and fluid type per well -> FormationTop rows (no top/base depth is
    published in this layer, so those columns stay None; never invented).

Licence: NSTA Open Data Licence (https://www.nstauthority.co.uk/footer/access-to-information/).
Wells are prefixed "GB: " on canonical_name to avoid collisions with Norwegian/Indian/US well names
that reuse short numeric-style identifiers.
"""
from __future__ import annotations

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
from app.ingest.sodir import split_sentences
from app.ingest.units import ft_to_m

UK = RAW_DIR / "uk" / "nsta"
LICENCE = "NSTA Open Data Licence (nstauthority.co.uk/footer/access-to-information)"
SOURCE = {
    "name": "NSTA (North Sea Transition Authority) Open Data",
    "country": "United Kingdom",
    "url": "https://opendata-nstauthority.hub.arcgis.com",
    "licence": LICENCE,
    "raw_dir": "uk",
}

UK_LAT_RANGE = (48.0, 63.0)   # sanity bounds for the UKCS (roughly 49-62N)
UK_LON_RANGE = (-10.0, 4.0)   # roughly 8W-3E, padded

_transformer_ed50 = None


def _ed50_to_wgs84(lon: float, lat: float) -> tuple[float, float]:
    """ED50 geographic (EPSG:4230) -> WGS84 geographic (EPSG:4326)."""
    global _transformer_ed50
    if _transformer_ed50 is None:
        from pyproj import Transformer
        _transformer_ed50 = Transformer.from_crs("EPSG:4230", "EPSG:4326", always_xy=True)
    lon2, lat2 = _transformer_ed50.transform(lon, lat)
    return lon2, lat2


def _f(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _epoch_to_date(ms) -> date | None:
    if not ms:
        return None
    try:
        return datetime.utcfromtimestamp(ms / 1000).date()
    except (TypeError, ValueError, OSError):
        return None


def _clean_text(s) -> str | None:
    if s is None:
        return None
    s = str(s).strip()
    return None if s in ("", "No Data Available") else s


def canonical_gb(regno: str) -> str:
    """'14/29a- 3' / '21/10-1' -> 'GB: 14/29a-3' (collapse the stray space NSTA puts before the suffix)."""
    s = re.sub(r"\s+", " ", (regno or "").strip())
    s = re.sub(r"-\s+", "-", s)
    s = re.sub(r"\s+-", "-", s)
    return f"GB: {s}"


def _coords(row: dict) -> tuple[float | None, float | None, str | None]:
    datum = (row.get("TOPHOLEDTM") or "").strip().upper()
    lon = _f(row.get("TOPHOLEXDD"))
    lat = _f(row.get("TOPHOLEYDD"))
    if lon is None or lat is None:
        return None, None, None
    if datum == "ED50":
        lon, lat = _ed50_to_wgs84(lon, lat)
    elif datum in ("WGS84", "ETRS89"):
        pass  # near-identical to WGS84 for our purposes (cm-level shift)
    else:
        return None, None, None  # unknown/BNG datum with no easting/northing given here -> don't guess
    if not (UK_LAT_RANGE[0] <= lat <= UK_LAT_RANGE[1] and UK_LON_RANGE[0] <= lon <= UK_LON_RANGE[1]):
        return None, None, None
    return lat, lon, f"NSTA wellbore top-hole layer, surface location (source datum {datum} -> WGS84)"


def _ingest_wellbores(db: Session, log) -> dict:
    path = UK / "wellbore_top_holes.json"
    if not path.exists():
        log("uk_nsta: missing wellbore_top_holes.json — run the NSTA download first")
        return {}
    rows = json.loads(path.read_text())
    wells: dict[str, Well] = {}
    stats: Counter = Counter()
    for r in rows:
        regno = _clean_text(r.get("WELLREGNO"))
        name = _clean_text(r.get("NAME"))
        stats["rows"] += 1
        lat, lon, pos_source = _coords(r)
        if lat is None and not regno and not name:
            stats["skipped_no_name_no_coords"] += 1
            continue
        if not regno:
            stats["skipped_no_regno"] += 1
            continue
        canon = canonical_gb(regno)
        if canon in wells:
            stats["duplicate_regno"] += 1
            continue

        td_md_m = _f(r.get("TDMDDEPM"))
        if td_md_m is None:
            td_md_m = ft_to_m(_f(r.get("TDMDDEPF")))
        td_tvd_m = _f(r.get("TDTVDSSM"))
        if td_tvd_m is None:
            td_tvd_m = ft_to_m(_f(r.get("TDTVDSSF")))
        kb_elev_m = _f(r.get("DATELEV_M"))
        if kb_elev_m is None:
            kb_elev_m = ft_to_m(_f(r.get("DATELEV_F")))
        water_depth_m = _f(r.get("WATDEP_M"))
        if water_depth_m is None:
            water_depth_m = ft_to_m(_f(r.get("WATDEP_F")))

        field_name = _clean_text(r.get("TARGETFLD"))
        operator = _clean_text(r.get("RESWOP")) or _clean_text(r.get("SUBAREAOP"))
        status = _clean_text(r.get("WELLBRSTAT")) or _clean_text(r.get("WELLOPSTAT")) or _clean_text(r.get("COMPLESTAT"))
        aliases = [name] if name and name != canon else []
        fact_url = _clean_text(r.get("WELLINFO"))

        w = Well(
            canonical_name=canon,
            aliases=aliases,
            field_name=field_name,
            country="United Kingdom",
            lat=lat, lon=lon,
            kb_elev_m=kb_elev_m,
            water_depth_m=water_depth_m,
            spud_date=_epoch_to_date(r.get("SPUDDATE")),
            td_md_m=td_md_m,
            td_tvd_m=td_tvd_m,
            status=status,
            purpose=_clean_text(r.get("ORIGINTENT")),
            well_type=_clean_text(r.get("DEVTYPE")),
            operator=operator,
            source="nsta",
            position_source=pos_source,
            external_id=_clean_text(r.get("WELLORIGIN")),
            fact_url=fact_url,
        )
        db.add(w)
        wells[canon] = w
        stats["wells"] += 1
        if lat is not None:
            stats["wells_with_coords"] += 1
    db.flush()
    return {"wells": wells, "stats": stats}


def _ingest_formation_tops(db: Session, wells: dict[str, Well], log) -> Counter:
    stats: Counter = Counter()
    path = UK / "expl_appraisal_results.json"
    if not path.exists():
        return stats
    rows = json.loads(path.read_text())
    for r in rows:
        regno = _clean_text(r.get("WELLREGNO"))
        if not regno:
            continue
        canon = canonical_gb(regno)
        w = wells.get(canon)
        if w is None:
            stats["formation_top_well_not_found"] += 1
            continue
        for n in (1, 2, 3, 4):
            fname = _clean_text(r.get(f"R{n}_NAME"))
            if not fname:
                continue
            age = _clean_text(r.get(f"R{n}_AGE"))
            rock = _clean_text(r.get(f"R{n}_ROCK"))
            top = FormationTop(
                well_id=w.id,
                formation=f"{fname} ({age})" if age else fname,
                lithology=rock,
                top_md_m=None, top_tvd_m=None, base_md_m=None,
                source="nsta",
                source_ref=f"NSTA exploration & appraisal well results — {regno}, reservoir {n}",
            )
            db.add(top)
            stats["formation_tops"] += 1
    db.flush()
    return stats


def _pdf_paragraphs(p: Path) -> list[list[str]]:
    """[[para, para, ...] per page] — pdfplumber text split on blank lines."""
    try:
        pages = pdf_pages(p)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for page_text in pages:
        paras, cur = [], []
        for line in page_text.split("\n"):
            s = line.strip()
            if not s:
                if cur:
                    paras.append(" ".join(cur))
                    cur = []
                continue
            cur.append(s)
        if cur:
            paras.append(" ".join(cur))
        out.append([re.sub(r"\s+", " ", x).strip() for x in paras if len(x.strip()) >= 20])
    return out


def _ingest_reports(db: Session, wells: dict[str, Well], log) -> Counter:
    stats: Counter = Counter()
    manifest_path = UK / "reports_manifest.json"
    reports_dir = UK / "reports"
    if not manifest_path.exists():
        return stats
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest:
        regno = _clean_text(entry.get("regno"))
        fname = entry.get("file")
        url = entry.get("url")
        if not regno or not fname:
            continue
        pdf_path = reports_dir / fname
        if not pdf_path.exists():
            stats["report_file_missing"] += 1
            continue
        canon = canonical_gb(regno)
        w = wells.get(canon)
        well_id = w.id if w is not None else None
        if w is None:
            stats["report_well_not_found"] += 1

        data = pdf_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        existing = db.query(Document).filter(Document.sha256 == sha).one_or_none()
        if existing is not None:
            stats["report_duplicate"] += 1
            continue

        pages = _pdf_paragraphs(pdf_path)
        n_pages = len(pages)
        if n_pages == 0 or sum(len(par) for page in pages for par in [page]) == 0:
            stats["report_unreadable"] += 1
            continue

        title = _clean_text(entry.get("name")) or f"NSTA legacy report — {regno}"
        doc = Document(
            well_id=well_id,
            kind="OTHER",
            title=title[:500],
            path=str(pdf_path.relative_to(RAW_DIR.parent)),
            url=url,
            report_date=None,
            pages=n_pages,
            is_scanned=False,
            ocr_mean_conf=None,
            sha256=sha,
            licence=LICENCE,
        )
        db.add(doc)
        db.flush()
        stats["documents"] += 1

        seq = 0
        for page_no, paras in enumerate(pages, start=1):
            for para_no, para in enumerate(paras, start=1):
                for sent_no, sent in enumerate(split_sentences(para), start=1):
                    if len(sent) < 15:
                        continue
                    seq += 1
                    db.add(Passage(
                        document_id=doc.id,
                        well_id=well_id,
                        locator=f"page {page_no}, para {para_no}.s{sent_no}",
                        seq=seq,
                        text=sent,
                        md_m=None,
                        report_date=None,
                    ))
                    stats["passages"] += 1
    db.flush()
    return stats


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    result = _ingest_wellbores(db, log)
    wells = result.get("wells", {})
    stats.update(result.get("stats", Counter()))
    if wells:
        stats.update(_ingest_formation_tops(db, wells, log))
        stats.update(_ingest_reports(db, wells, log))

    n_wells = stats.get("wells", 0)
    n_docs = stats.get("documents", 0)
    if n_wells:
        db.add(DataSource(
            name="NSTA UKCS offshore wellbore top holes (WGS84) — well header, location, TD, operator, field, status",
            url="https://opendata-nstauthority.hub.arcgis.com",
            licence=LICENCE,
            records=n_wells,
            notes=f"{stats.get('wells_with_coords', 0)} wells with usable WGS84 coordinates (ED50 points reprojected with pyproj)",
        ))
    if stats.get("formation_tops"):
        db.add(DataSource(
            name="NSTA UKCS exploration & appraisal well results (ED50) — target/reservoir name, age, rock, fluid",
            url="https://opendata-nstauthority.hub.arcgis.com",
            licence=LICENCE,
            records=stats["formation_tops"],
            notes="no top/base depth published in this layer; formation names only",
        ))
    if n_docs:
        db.add(DataSource(
            name="NSTA legacy well reports (mostly Shell geochemistry investigations), linked from the wellbore-reports layer",
            url="https://opendata-nstauthority.hub.arcgis.com",
            licence=LICENCE,
            records=n_docs,
            notes=f"{stats.get('passages', 0)} citable passages extracted; capped sample, not the full 470-report set",
        ))
    db.flush()

    log(f"uk_nsta: {dict(stats)}")
    return dict(stats)
