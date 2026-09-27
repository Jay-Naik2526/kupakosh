"""V3: 3D subsurface scene API (docs/PLAN_V2.md — "3D subsurface room").

GET /api/wells/{id}/scene?radius_m=&bit_md=

Returns the active well plus its offset wells (reuses app.engines.offsets.offsets_for_well),
each with a surface position in *local metres relative to the active well* (equirectangular
projection — fine for the radii this app uses, <= 50 km; noted in the response), a 3D
trajectory (real survey when we have one, otherwise a vertical line to TD flagged
`assumed_vertical`), formation tops and trusted events along that trajectory, all carrying
their `source_ref` so the frontend can open the same source slip as everywhere else.

Convention: x = east (m), y = north (m), z = -TVD (m, so depth is negative / "down").
No invented numbers: a well with no lat/lon is skipped; a well with no survey is shown
vertical and labelled; formation tops without a TVD fall back to MD for z (noted per point).
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import cfg, lithology
from app.db.models import SurveyStation, Well
from app.db.session import get_db
from app.engines import lookahead as la
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.offsets import offsets_for_well

router = APIRouter(prefix="/api")

EARTH_R_M = 6371008.8
PROJECTION_NOTE = "equirectangular projection around the active well's surface location; adequate for radii up to ~50 km"


def _local_xy(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    """Metres (x=east, y=north) of (lat, lon) relative to (lat0, lon0). Equirectangular — see PROJECTION_NOTE."""
    dlat = math.radians(lat - lat0)
    dlon = math.radians(lon - lon0)
    x = EARTH_R_M * dlon * math.cos(math.radians(lat0))
    y = EARTH_R_M * dlat
    return x, y


def _trajectory(db: Session, well: Well, sx: float, sy: float) -> tuple[list[dict], bool]:
    """Trajectory points [{md, x, y, z}] in scene metres. Real survey when present, else a
    vertical line to td_md_m flagged assumed_vertical=true. z = -TVD (m)."""
    stations = list(db.scalars(select(SurveyStation).where(SurveyStation.well_id == well.id).order_by(SurveyStation.md_m)))
    stations = [s for s in stations if s.md_m is not None]
    if stations:
        pts = []
        for s in stations:
            tvd = s.tvd_m if s.tvd_m is not None else s.md_m  # no TVD recorded: fall back to MD (near-vertical sections only)
            north = s.north_m or 0.0
            east = s.east_m or 0.0
            pts.append({"md": round(s.md_m, 1), "x": round(sx + east, 2), "y": round(sy + north, 2), "z": round(-tvd, 2)})
        return pts, False
    if not well.td_md_m:
        return [], True
    return [{"md": 0.0, "x": round(sx, 2), "y": round(sy, 2), "z": 0.0},
            {"md": round(well.td_md_m, 1), "x": round(sx, 2), "y": round(sy, 2), "z": round(-well.td_md_m, 2)}], True


def _interp_xy(traj: list[dict], md: float) -> tuple[float, float]:
    """x/y at a given MD by linear interpolation along the trajectory (flat extrapolation past the ends).
    Used to place formation tops and events, which only carry MD/TVD, in the 3D scene."""
    if not traj:
        return 0.0, 0.0
    if md <= traj[0]["md"]:
        return traj[0]["x"], traj[0]["y"]
    if md >= traj[-1]["md"]:
        return traj[-1]["x"], traj[-1]["y"]
    for a, b in zip(traj, traj[1:]):
        if a["md"] <= md <= b["md"]:
            span = b["md"] - a["md"]
            f = (md - a["md"]) / span if span > 0 else 0.0
            return a["x"] + f * (b["x"] - a["x"]), a["y"] + f * (b["y"] - a["y"])
    return traj[-1]["x"], traj[-1]["y"]


def _tops(well_id: int, traj: list[dict]) -> list[dict]:
    cx = ctx()
    lith = lithology()
    out = []
    for t in cx.tops.tops(well_id):
        if t.top_md_m is None:
            continue
        z = -(t.top_tvd_m if t.top_tvd_m is not None else t.top_md_m)
        x, y = _interp_xy(traj, t.top_md_m)
        out.append({"formation": t.formation, "label": pretty(t.formation), "md": round(t.top_md_m, 1),
                    "x": round(x, 2), "y": round(y, 2), "z": round(z, 2), "z_is_approx_md": t.top_tvd_m is None,
                    "lithology": t.lithology or lith.get(t.formation), "source_ref": t.source_ref})
    return out


def _events(well_id: int, traj: list[dict]) -> list[dict]:
    cx = ctx()
    out = []
    for e in cx.events.get(well_id, []):
        if e.md_m is None:
            continue
        z = -(e.tvd_m if e.tvd_m is not None else e.md_m)
        x, y = _interp_xy(traj, e.md_m)
        out.append({"id": e.id, "hazard": e.hazard, "md": round(e.md_m, 1), "x": round(x, 2), "y": round(y, 2),
                    "z": round(z, 2), "formation": e.formation, "source_ref": e.source_ref, "evidence": e.evidence_span,
                    "confidence": e.confidence})
    return out


def _well_node(db: Session, w: Well, lat0: float, lon0: float, *, is_active: bool, offset_info: dict | None = None) -> dict:
    sx, sy = (0.0, 0.0) if is_active else _local_xy(lat0, lon0, w.lat, w.lon)
    traj, assumed_vertical = _trajectory(db, w, sx, sy)
    node = {
        "well_id": w.id, "name": w.canonical_name, "country": w.country, "field": w.field_name,
        "lat": w.lat, "lon": w.lon, "x": round(sx, 2), "y": round(sy, 2),
        "is_active": is_active, "assumed_vertical": assumed_vertical,
        "td_md_m": w.td_md_m, "td_tvd_m": w.td_tvd_m,
        "trajectory": traj,
        "formation_tops": _tops(w.id, traj),
        "events": _events(w.id, traj),
    }
    if offset_info is not None:
        node["distance_m"] = offset_info["raw"]["distance_m"]
        node["similarity"] = offset_info["sim"]
        node["similarity_components"] = offset_info["components"]
        node["documented"] = offset_info["documented"]
    return node


@router.get("/wells/{well_id}/scene")
def well_scene(well_id: int, radius_m: float | None = None, bit_md: float | None = None, db: Session = Depends(get_db)):
    w = db.get(Well, well_id)
    if not w:
        raise HTTPException(404, "well not found")
    if w.lat is None or w.lon is None:
        raise HTTPException(422, "well has no surface location — cannot place it in the 3D scene")
    max_offsets = cfg()["offsets"]["max_offsets"]
    offsets = offsets_for_well(well_id, radius_m=radius_m)[:max_offsets]
    wells = [_well_node(db, w, w.lat, w.lon, is_active=True)]
    for o in offsets:
        ow = db.get(Well, o["well_id"])
        if ow is None or ow.lat is None or ow.lon is None:
            continue
        wells.append(_well_node(db, ow, w.lat, w.lon, is_active=False, offset_info=o))
    out = {
        "active_well_id": well_id, "radius_m": radius_m or cfg()["offsets"]["default_radius_m"],
        "projection": PROJECTION_NOTE, "z_convention": "z = -TVD in metres (down is negative)",
        "n_wells": len(wells), "n_offsets": len(wells) - 1, "wells": wells,
    }
    if bit_md is not None:
        out["lookahead"] = la.assess(db, well_id, bit_md)
    return out
