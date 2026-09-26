"""Canadian public well headers (no login) -> wells.

Three independent, freely queryable ArcGIS/ESRI REST services, each mirroring a provincial or
federal offshore regulator's own public register. No narrative well-history documents were found
that could be downloaded without registering for an account (see data/raw/canada/REPORT.md for
what was tried and rejected: CNSOPB's own Data Management Centre, NL's report hub, Alberta's ST37).

  * Nova Scotia offshore (CNSOPB / "CNSOEB"): "CNSOEB Directory of Wells 2022" layer, served by
    NRCan's federal geo.ca mirror of the regulator's own map service.
      data/raw/canada/cnsopb_wells/directory_of_wells.json
  * Newfoundland & Labrador offshore (C-NLOPB): Exploration / Delineation / Development /
    Dual-classified well layers on the board's own ArcGIS Online organisation.
      data/raw/canada/cnlopb_wells/*.json
  * Saskatchewan (Ministry of Energy and Resources, via gis.saskatchewan.ca "Economy/Petroleum"
    service, "Vertical Wells" layer): the full table is ~119,400 wells with a free-text depth
    field, so a numeric server-side filter is impossible; we keep a DOCUMENTED SUBSET of the
    6,000 most recently added rows (by OBJECTID) that do have a bottom-hole TVD, in 2,000-row
    pages (service maxRecordCount=2000). This is not "all Saskatchewan wells" — see REPORT.md.
      data/raw/canada/sask_wells/wells_recent.json

Alberta AER's ST37 was checked (services2.arcgis.com/.../AB_Well_Licence_WebM, 475,125 wells) and
rejected: the public map layer carries only a well-type/category symbol and coordinates, no UWI,
no operator, no spud date, no depth — there is nothing there to responsibly attach to our schema
without inventing fields, and the real ST37 file is order-only (informationrequest@aer.ca).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.config import RAW_DIR
from app.db.models import DataSource, Well

SOURCE = {
    "name": "Canadian public well headers (NS/NL/SK)",
    "country": "Canada",
    "url": "https://maps-cartes.services.geo.ca ; https://services5.arcgis.com/JZPISF0sj1UatnZ8 ; https://gis.saskatchewan.ca",
    "licence": "Open Government Licence - Canada / C-NLOPB open data / Government of Saskatchewan open data",
    "raw_dir": "canada",
}
CA = RAW_DIR / "canada"

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _f(v) -> float | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _strip_unit_m(v) -> float | None:
    """CNLOPB depths/water depths are strings like '3657.6m' or '114m' (occasionally blank)."""
    if v is None or not str(v).strip():
        return None
    m = _NUM.search(str(v))
    return float(m.group()) if m else None


def _cnsopb_date(s: str | None) -> date | None:
    """'7-Jun-67' etc. Python's strptime %y pivots 00-68 -> 2000s, which is wrong for a dataset of
    1967-2015 offshore wells; every CNSOPB well predates 2015, so any parsed year > 2015 is really
    19xx."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = datetime.strptime(s, "%d-%b-%y").date()
    except ValueError:
        return None
    if d.year > 2015:
        d = d.replace(year=d.year - 100)
    return d


def _cnlopb_date(s: str | None) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%B %d, %Y").date()
    except ValueError:
        return None


def _epoch_ms_date(ms) -> date | None:
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
    except (ValueError, OSError, OverflowError, TypeError):
        return None


def _load(path):
    """Handles both the ArcGIS query response shape ({"features": [...]}) and the plain list
    the one-off download script wrote for the Saskatchewan subset."""
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    return data.get("features", [])


# ---------------------------------------------------------------- Nova Scotia (CNSOPB)
def _ingest_cnsopb(db: Session, stats: Counter, seen: set[str]) -> None:
    feats = _load(CA / "cnsopb_wells" / "directory_of_wells.json")
    for feat in feats:
        a = feat.get("attributes", {})
        geom = feat.get("geometry") or {}
        well_name = (a.get("Well_Name") or "").strip()
        designation = (a.get("Well_Nam_1") or "").strip()
        name = " ".join(x for x in (well_name, designation) if x).strip()
        if not name:
            stats["cnsopb_skipped_no_name"] += 1
            continue
        canonical_name = f"CA: {name}"
        if canonical_name in seen:
            stats["cnsopb_skipped_duplicate"] += 1
            continue
        seen.add(canonical_name)

        lat = _f(a.get("latitude_d")) or _f(geom.get("y"))
        lon = _f(a.get("longitud_1")) or _f(geom.get("x"))
        result = (a.get("Well") or "").strip() or None
        status = (a.get("Well_1") or "").strip() or None

        w = Well(
            canonical_name=canonical_name,
            aliases=[well_name, designation] if designation else [well_name],
            country="Canada",
            field_name="Scotian Basin (offshore Nova Scotia)",
            lat=lat, lon=lon,
            kb_elev_m=_f(a.get("RT_Elevati")),
            water_depth_m=_f(a.get("Water_Dept")),
            spud_date=_cnsopb_date(a.get("Spud_Date")),
            td_md_m=_f(a.get("Total_Dept")),  # already metres (Total_De_1 is the ft equivalent)
            status=status,
            well_type=(a.get("Well_Type") or None),
            purpose=result,
            operator=(a.get("Company") or None),
            source="cnsopb",
            position_source="CNSOEB Directory of Wells 2022 (NRCan geo.ca mirror, decimal degrees)" if lat is not None else None,
            external_id=None,
            fact_url="https://cnsoer.ca",
        )
        db.add(w)
        stats["cnsopb_wells"] += 1


# ---------------------------------------------------------------- Newfoundland & Labrador (C-NLOPB)
_CNLOPB_FILES = [
    "Exploration_Wells_View.json",
    "Delineation_Wells_View.json",
    "Development_Wells_View.json",
    "Dual_Classified_Wells_View.json",
]


def _ingest_cnlopb(db: Session, stats: Counter, seen: set[str]) -> None:
    seen_uwi: set[str] = set()
    for fname in _CNLOPB_FILES:
        feats = _load(CA / "cnlopb_wells" / fname)
        for feat in feats:
            a = feat.get("attributes", {})
            name = (a.get("Wellname") or "").strip()
            uwi = (a.get("UWI") or "").strip() or None
            if not name:
                stats["cnlopb_skipped_no_name"] += 1
                continue
            if uwi and uwi in seen_uwi:
                stats["cnlopb_skipped_duplicate"] += 1
                continue
            canonical_name = f"CA: {name}"
            if canonical_name in seen:
                canonical_name = f"CA: {name} ({uwi or a.get('WellNumber')})"
            if canonical_name in seen:
                stats["cnlopb_skipped_duplicate"] += 1
                continue
            seen.add(canonical_name)
            if uwi:
                seen_uwi.add(uwi)

            lat = _f(a.get("DecimalLat"))
            lon = _f(a.get("DecimalLon"))
            w = Well(
                canonical_name=canonical_name,
                aliases=[name] + ([a["WellNumber"]] if a.get("WellNumber") else []),
                country="Canada",
                field_name="Jeanne d'Arc / Flemish Pass (offshore Newfoundland & Labrador)",
                lat=lat, lon=lon,
                water_depth_m=_strip_unit_m(a.get("WaterDepth")),
                spud_date=_cnlopb_date(a.get("SpudDate")),
                td_md_m=_strip_unit_m(a.get("TotDpthMD")),
                status=(a.get("WellStatus") or None),
                well_type=(a.get("Classifi") or None),
                operator=(a.get("Operator") or None),
                source="cnlopb",
                position_source="C-NLOPB well inventory (ArcGIS, decimal degrees)" if lat is not None else None,
                external_id=uwi or a.get("WellNumber"),
                fact_url="https://home-cnlopb.hub.arcgis.com/pages/well-inventory",
            )
            db.add(w)
            stats["cnlopb_wells"] += 1
            stats[f"cnlopb_wells_{fname.split('_Wells_')[0].lower()}"] += 1


# ---------------------------------------------------------------- Saskatchewan
def _ingest_sask(db: Session, stats: Counter, seen: set[str]) -> None:
    feats = _load(CA / "sask_wells" / "wells_recent.json")
    for feat in feats:
        a = feat.get("attributes", {})
        cwi = (a.get("WELL_CWI") or "").strip()
        name = (a.get("LEGACYWELLNAME") or "").strip() or cwi or (a.get("WELLBORE_UWI") or "").strip()
        if not name:
            stats["sask_skipped_no_name"] += 1
            continue
        canonical_name = f"CA: {name}"
        if canonical_name in seen and cwi:
            canonical_name = f"CA: {name} ({cwi})"
        if canonical_name in seen:
            stats["sask_skipped_duplicate"] += 1
            continue
        seen.add(canonical_name)

        lat = _f(a.get("SURFACELATITUDE"))
        lon = _f(a.get("SURFACELONGITUDE"))
        operator = (a.get("WELLLICENCEBUSINESSASSOCIATE") or None)
        if operator:
            operator = re.sub(r"\s*\[\d+\]\s*$", "", operator).strip()

        w = Well(
            canonical_name=canonical_name,
            aliases=[x for x in (name, cwi, a.get("WELLBORE_UWI")) if x],
            country="Canada",
            field_name=(a.get("SURFACEGEOAREA") or None),
            lat=lat, lon=lon,
            spud_date=_epoch_ms_date(a.get("WELLDERIVEDSPUDDATE")),
            td_md_m=_strip_unit_m(a.get("WELLBORE_BH_MEASUREDDEPTH")),
            td_tvd_m=_strip_unit_m(a.get("WELLBORE_BH_TRUEVERTICALDEPTH")),
            status=(a.get("WELLSTATUS") or None),
            well_type=(a.get("WELLDRILLINGTRAJECTORY") or None),
            operator=operator,
            source="sask_energy",
            position_source="Saskatchewan Economy/Petroleum GIS service (NAD83 CSRS, treated as WGS84 at this scale)" if lat is not None else None,
            external_id=cwi or None,
            fact_url="https://gis.saskatchewan.ca/arcgis/rest/services/Economy/Petroleum/MapServer/0",
        )
        db.add(w)
        stats["sask_wells"] += 1


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    seen: set[str] = set()

    _ingest_cnsopb(db, stats, seen)
    db.flush()
    log(f"ca_wells: {stats['cnsopb_wells']} Nova Scotia (CNSOPB) wells")

    _ingest_cnlopb(db, stats, seen)
    db.flush()
    log(f"ca_wells: {stats['cnlopb_wells']} Newfoundland & Labrador (C-NLOPB) wells")

    _ingest_sask(db, stats, seen)
    db.flush()
    log(f"ca_wells: {stats['sask_wells']} Saskatchewan wells (documented subset)")

    total = stats["cnsopb_wells"] + stats["cnlopb_wells"] + stats["sask_wells"]
    db.add(DataSource(
        name="CNSOEB Directory of Wells 2022 (Nova Scotia offshore)",
        url="https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/Nova_Scotia_Offshore_Petroleum_en/MapServer/0",
        licence="Open Government Licence - Canada", records=stats["cnsopb_wells"],
        notes="Nova Scotia offshore well headers. No narrative reports: CNSOPB's Data Management Centre requires a registered account.",
    ))
    db.add(DataSource(
        name="C-NLOPB well inventory (NL offshore)",
        url="https://home-cnlopb.hub.arcgis.com/pages/well-inventory",
        licence="C-NLOPB open data (public)", records=stats["cnlopb_wells"],
        notes="Exploration + Delineation + Development + Dual-classified NL offshore well headers.",
    ))
    db.add(DataSource(
        name="Saskatchewan petroleum wells (subset)",
        url="https://gis.saskatchewan.ca/arcgis/rest/services/Economy/Petroleum/MapServer/0",
        licence="Government of Saskatchewan open data", records=stats["sask_wells"],
        notes="Documented subset: 6,000 of ~119,400 wells (most recent OBJECTIDs with a non-null bottom-hole TVD); "
              "the full table's depth field is free text and cannot be filtered numerically server-side.",
    ))
    db.flush()
    log(f"ca_wells: total {total} Canadian wells")
    return dict(stats)
