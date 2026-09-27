"""V2 USP: Global Analog Memory for Indian basins (docs/PLAN_V2.md).

Not yet wired into app/main.py — the lead should add `routes_analogs` to the import and
`for r in (...)` loop in app/main.py (see this file's tests for how to include it standalone).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.engines.analogs import acfg, basin_suggestions, find_analogs

router = APIRouter(prefix="/api")


@router.get("/analogs")
def analogs(lithology: str = Query(..., description="sandstone | shale | claystone | limestone (or carbonate) | "
                                                       "chalk | marl | coal | salt (or evaporite) | basement (or granite) | mixed"),
            top: float = Query(..., description="depth band top, metres MD"),
            base: float = Query(..., description="depth band base, metres MD"),
            hazard: str | None = Query(None, description="comma-separated hazard keys; omit for all taxonomy hazards"),
            basin: str | None = Query(None, description="Indian basin slug, e.g. 'assam-arakan' — informational only")):
    hazards = [h.strip() for h in hazard.split(",") if h.strip()] if hazard else None
    result = find_analogs(lithology, top, base, hazards=hazards, basin=basin)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/analogs/classes")
def analog_classes():
    """The lithology classes accepted by /api/analogs, for building a query form."""
    a = acfg()
    return {"classes": a["classes"], "aliases": a["class_aliases"]}


@router.get("/analogs/basins")
def analogs_basins():
    """Indian basins with lithology/formation/depth suggestions grounded in that basin's own NDR
    summary passages (never invented — see app.engines.analogs.basin_suggestions)."""
    return {"basins": basin_suggestions()}
