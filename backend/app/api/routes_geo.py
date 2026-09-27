"""Compact well-map geometry (V4: the map screen).

GET /api/geo/wells   -> ALL located wells (~97k) as a compact array payload (not GeoJSON — GeoJSON's per-
    feature object/array boilerplate roughly doubles the payload at this row count). country and kind are
    index-encoded against the `countries` / `kinds` arrays so the repeated strings aren't sent per row.
    Gzip does the rest: ask the lead to add `app.add_middleware(GZipMiddleware, minimum_size=1000)` in
    main.py (not present yet) so this and other big JSON responses compress in transit.
GET /api/geo/basins  -> Indian basins (app.db.models.Basin) as bbox rectangles, GeoJSON FeatureCollection
    (small: a handful of features, so GeoJSON's readability is worth the bytes here).

Both read from the shared in-memory `ctx()` (app.engines.context) / a plain DB query — no per-request
DB scan of the well table. `reset_cache()` mirrors `ctx.reset()` and should be called after a rebuild.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter
from sqlalchemy import select

from app.db.models import Basin
from app.db.session import SessionLocal
from app.engines.context import ctx

router = APIRouter(prefix="/api")

# Well.well_type values that are not a single physical well (BSEE block aggregates, field centroids) — see
# NOT_WELLS in routes.py. Kept as its own tuple here so this module has no import-time dependency on routes.py.
_NOT_WELLS = {"block_aggregate", "field_centroid"}
_KINDS = ["well", "block_aggregate", "field_centroid"]
GEO_FIELDS = ["id", "name", "country_idx", "lat", "lon", "has_events", "n_events", "documented", "kind_idx", "top_hazard_idx"]


def _kind_of(well_type: str | None) -> str:
    return well_type if well_type in _NOT_WELLS else "well"


def _top_hazard(events: list) -> str | None:
    """Most frequent hazard among a well's trusted events (ties broken by first-seen order); None if no events."""
    if not events:
        return None
    counts: dict[str, int] = {}
    for e in events:
        if e.hazard:
            counts[e.hazard] = counts.get(e.hazard, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


@lru_cache(maxsize=1)
def _rows() -> tuple[list[str], list[list], list[str]]:
    cx = ctx()
    countries: list[str] = []
    cidx: dict[str, int] = {}
    hazards: list[str] = []
    hidx: dict[str, int] = {}
    rows: list[list] = []
    for w in cx.wells.values():
        if w.lat is None or w.lon is None:
            continue
        c = w.country or "unknown"
        i = cidx.get(c)
        if i is None:
            i = cidx[c] = len(countries)
            countries.append(c)
        w_events = cx.events.get(w.id, [])
        n_events = len(w_events)
        th = _top_hazard(w_events)
        hi = -1
        if th is not None:
            hi = hidx.get(th)
            if hi is None:
                hi = hidx[th] = len(hazards)
                hazards.append(th)
        rows.append([w.id, w.canonical_name, i, round(w.lat, 4), round(w.lon, 4),
                     1 if n_events > 0 else 0, n_events, 1 if w.id in cx.documented else 0,
                     _KINDS.index(_kind_of(w.well_type)), hi])
    return countries, rows, hazards


def reset_cache() -> None:
    _rows.cache_clear()


@router.get("/geo/wells")
def geo_wells(country: str | None = None):
    """Compact array payload for every located well. `country`, if given, is the English name as stored
    on well.country (e.g. "India", "Norway") — matches the values in GET /api/countries. `top_hazard_idx`
    indexes into `hazards` (the well's most frequent recorded hazard), or -1 if the well has no events."""
    countries, rows, hazards = _rows()
    out_rows = rows if not country else [r for r in rows if countries[r[2]] == country]
    return {"n": len(out_rows), "countries": countries, "kinds": _KINDS, "hazards": hazards,
            "fields": GEO_FIELDS, "rows": out_rows}


@router.get("/geo/basins")
def geo_basins():
    """Indian sedimentary basins with a bbox (rectangle) geometry, for the map overlay + analogs link."""
    with SessionLocal() as db:
        feats = []
        for b in db.scalars(select(Basin).order_by(Basin.name)):
            if not b.bbox or len(b.bbox) != 4:
                continue
            min_lon, min_lat, max_lon, max_lat = b.bbox
            ring = [[min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]]
            feats.append({"type": "Feature",
                          "properties": {"name": b.name, "slug": b.slug, "url": b.url, "category": b.category},
                          "geometry": {"type": "Polygon", "coordinates": [ring]}})
    return {"type": "FeatureCollection", "features": feats}
