"""Offset-well selection: radius + similarity (SPEC.md §9.4).

sim = w_geo * exp(-d / D) + w_strat * Jaccard(formation sets) + w_depth * overlap(TD ranges)
Every component is returned so the UI can show why a well ranks where it does.
"""
from __future__ import annotations

import math

from app.config import cfg
from app.engines.context import ctx, haversine_m


def jaccard(a: set, b: set) -> float | None:
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


def td_overlap(td_a: float | None, td_b: float | None) -> float | None:
    if not td_a or not td_b:
        return None
    return min(td_a, td_b) / max(td_a, td_b)


def similarity(d_m: float, jac: float | None, ovl: float | None) -> dict:
    c = cfg()["offsets"]
    geo = math.exp(-d_m / c["D_m"])
    parts = {"geo": c["w_geo"] * geo, "strat": c["w_strat"] * (jac or 0.0), "depth": c["w_depth"] * (ovl or 0.0)}
    return {"sim": round(sum(parts.values()), 4), "components": {k: round(v, 4) for k, v in parts.items()},
            "raw": {"distance_m": round(d_m), "geo_decay": round(geo, 4), "jaccard": None if jac is None else round(jac, 3),
                    "td_overlap": None if ovl is None else round(ovl, 3)}}


def find_offsets(lat: float, lon: float, radius_m: float | None = None, exclude_id: int | None = None,
                 formations: set[str] | None = None, td_m: float | None = None, documented_only: bool = False,
                 limit: int | None = None) -> list[dict]:
    c = cfg()["offsets"]
    cx = ctx()
    radius_m = min(radius_m or c["default_radius_m"], c["max_radius_m"])
    dlat = radius_m / 111_000
    out = []
    for w in cx.wells.values():
        if w.id == exclude_id or w.lat is None or abs(w.lat - lat) > dlat:
            continue
        d = haversine_m(lat, lon, w.lat, w.lon)
        if d > radius_m:
            continue
        documented = w.id in cx.documented
        if documented_only and not documented:
            continue
        s = similarity(d, jaccard(formations or set(), cx.tops.penetrated(w.id)), td_overlap(td_m, w.td_md_m))
        out.append({"well_id": w.id, "name": w.canonical_name, "field": w.field_name, "lat": w.lat, "lon": w.lon,
                    "td_md_m": w.td_md_m, "documented": documented, "n_events": len(cx.events.get(w.id, [])), **s})
    out.sort(key=lambda r: (-r["sim"], r["raw"]["distance_m"]))
    return out[: limit or c["max_offsets"]]


def offsets_for_well(well_id: int, radius_m: float | None = None, documented_only: bool = False) -> list[dict]:
    cx = ctx()
    w = cx.wells[well_id]
    if w.lat is None:
        return []
    return find_offsets(w.lat, w.lon, radius_m, exclude_id=well_id, formations=cx.tops.penetrated(well_id),
                        td_m=w.td_md_m, documented_only=documented_only)
