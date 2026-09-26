"""New Zealand Petroleum & Minerals (NZP&M) -> wells (headers only).

Public ArcGIS FeatureServer used by NZP&M's own "petroleum-webmaps" page, no login required.
Licence: CC-BY 4.0 (New Zealand Government / MBIE open data).

Raw data: data/raw/nz/nzpam_wells/wells_raw.json — every feature ("Petroleum Wells" layer,
id 18) of https://services3.arcgis.com/fp1tibNcN9mbExhG/arcgis/rest/services/Petroleum_and_minerals/
FeatureServer, fetched with outSR=4326 so LatitudeDD/LongtudeDD are already WGS84 decimal degrees.

Well completion reports (PR-numbered) were NOT ingested: NZP&M's exploration-reports catalogue at
data.nzpam.govt.nz is a CKAN "Geodata Catalogue" that is discoverable without an account but blocks
scripted access with a bot-detection layer, and PDF *download* of any report additionally requires
a free RealMe login — both are out of scope for a no-login ingester. See data/raw/nz/REPORT.md.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.config import RAW_DIR
from app.db.models import DataSource, Well
from app.ingest.units import ft_to_m

SOURCE = {
    "name": "NZP&M petroleum wells",
    "country": "New Zealand",
    "url": "https://services3.arcgis.com/fp1tibNcN9mbExhG/arcgis/rest/services/Petroleum_and_minerals/FeatureServer/18",
    "licence": "CC-BY 4.0 (New Zealand Petroleum & Minerals / MBIE open data)",
    "raw_dir": "nz",
}
NZ = RAW_DIR / "nz"
LICENCE = SOURCE["licence"]


def _date(ms) -> date | None:
    """SpudDate/ComplnDate are epoch milliseconds (can be negative for pre-1970 wells)."""
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()
    except (ValueError, OSError, OverflowError):
        return None


def _num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_m(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    if (unit or "").strip().lower() in ("ft", "feet", "'"):
        return ft_to_m(value)
    return value


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    path = NZ / "nzpam_wells" / "wells_raw.json"
    if not path.exists():
        log("nz_wells: no raw data found, skipping")
        return dict(stats)

    feats = json.loads(path.read_text())
    seen: set[str] = set()
    for feat in feats:
        a = feat.get("attributes", {})
        name = (a.get("FullName") or a.get("PBWellID") or "").strip()
        if not name:
            stats["skipped_no_name"] += 1
            continue
        canonical_name = f"NZ: {name}"
        if canonical_name in seen:
            # keep going rather than silently dropping a real well row (SPEC.md: invent nothing,
            # but also never lose a distinct record) — disambiguate with the PBWellID
            canonical_name = f"NZ: {name} ({a.get('PBWellID')})"
            stats["disambiguated"] += 1
        if canonical_name in seen:
            stats["skipped_duplicate"] += 1
            continue
        seen.add(canonical_name)

        lat, lon = _num(a.get("LatitudeDD")), _num(a.get("LongtudeDD"))
        td_md_m = _to_m(_num(a.get("TotalMD")), a.get("TotMDunit"))
        td_tvd_m = _to_m(_num(a.get("TVD")), a.get("TVDUnit"))
        water_depth_m = _to_m(_num(a.get("WaterDepth")), a.get("DepthUnit"))
        kb_elev_m = _to_m(_num(a.get("Elevation")), a.get("ElevUnit"))

        aliases = [name]
        if a.get("PBWellID") and a.get("PBWellID") != name:
            aliases.append(a["PBWellID"])

        w = Well(
            canonical_name=canonical_name,
            aliases=aliases,
            country="New Zealand",
            field_name=None,
            lat=lat, lon=lon,
            kb_elev_m=kb_elev_m,
            water_depth_m=water_depth_m,
            spud_date=_date(a.get("SpudDate")),
            td_md_m=td_md_m,
            td_tvd_m=td_tvd_m,
            status=(a.get("Status") or None),
            well_type=(a.get("WellType") or None),
            operator=(a.get("Operator") or None),
            source="nzpam",
            position_source="NZP&M ArcGIS FeatureServer (WGS84 decimal degrees)" if lat is not None else None,
            external_id=a.get("PBWellID"),
            fact_url=SOURCE["url"],
        )
        db.add(w)
        stats["wells"] += 1
    db.flush()

    db.add(DataSource(
        name=SOURCE["name"], url=SOURCE["url"], licence=LICENCE, records=stats["wells"],
        notes="New Zealand petroleum well headers (Taranaki Basin and others). No narrative well "
              "completion reports ingested: NZP&M's PR report catalogue needs a RealMe login to download PDFs.",
    ))
    log(f"nz_wells: {dict(stats)}")
    return dict(stats)
