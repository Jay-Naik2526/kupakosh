from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.brief.prespud import build, render_html, render_pdf
from app.db.session import get_db

router = APIRouter(prefix="/api")


class BriefIn(BaseModel):
    lat: float
    lon: float
    target_td_m: float
    planned_tops: list[dict] | None = None
    radius_m: float | None = None


@router.post("/brief")
def brief(body: BriefIn, db: Session = Depends(get_db)):
    return build(db, body.lat, body.lon, body.target_td_m, body.planned_tops, body.radius_m)


@router.post("/brief/html", response_class=HTMLResponse)
def brief_html(body: BriefIn, db: Session = Depends(get_db)):
    return render_html(build(db, body.lat, body.lon, body.target_td_m, body.planned_tops, body.radius_m))


@router.post("/brief/pdf")
def brief_pdf(body: BriefIn, db: Session = Depends(get_db)):
    b = build(db, body.lat, body.lon, body.target_td_m, body.planned_tops, body.radius_m, final=True)
    try:
        pdf = render_pdf(b)
    except OSError as e:  # pango not found
        raise HTTPException(503, f"PDF renderer unavailable: {e}. Use /api/brief/html and print to PDF.")
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{b["ref_no"].replace("/", "-")}.pdf"'})
