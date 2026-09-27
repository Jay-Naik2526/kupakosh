"""USP1 (docs/PLAN_V2.md): the Hindsight Test — blind replay proof."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.engines import hindsight as hs

router = APIRouter(prefix="/api/hindsight")


@router.get("/summary")
def summary(max_wells: int | None = None, country: str | None = None, source: str | None = None):
    s = hs.summary(max_wells)
    if source:
        strat = s["by_source"].get(source)
        if strat is None:
            raise HTTPException(404, f"no cells for source {source!r}")
        return {"source": source, "alert_mode_config": s["alert_mode_config"], "rr_min_config": s["rr_min_config"],
                "headline": strat["lift"]["headline"], **strat}
    if country:
        strat = s["by_country"].get(country)
        if strat is None:
            raise HTTPException(404, f"no cells for country {country!r}")
        return {"country": country, "alert_mode_config": s["alert_mode_config"], "rr_min_config": s["rr_min_config"],
                "headline": strat["lift"]["headline"], **strat}
    return s


@router.get("/wells")
def wells(max_wells: int | None = None, country: str | None = None, source: str | None = None):
    s = hs.summary(max_wells)
    rows = s["wells"]
    if country:
        rows = [r for r in rows if r["country"] == country]
    if source:
        rows = [r for r in rows if r["source"] == source]
    return sorted(rows, key=lambda r: -r["events"])


@router.get("/{well_id}")
def well(well_id: int):
    try:
        return hs.run_well(well_id)
    except KeyError:
        raise HTTPException(404, "well not found")


@router.post("/recompute")
def recompute(max_wells: int | None = None):
    """Bypass the cache — used by bootstrap/eval, and available for a manual refresh."""
    return hs.recompute(max_wells)
