"""POST /api/ingest (upload a report -> background job) and GET /api/jobs/{id} (SPEC.md §10)."""
from __future__ import annotations

import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import cfg
from app.ingest import upload

router = APIRouter(prefix="/api")
ALLOWED = (".pdf", ".txt", ".html", ".htm", ".xml")


@router.post("/ingest")
async def ingest(file: UploadFile = File(...), kind: str = Form("DDR_PDF"), well: str | None = Form(None),
                 country: str | None = Form(None), lat: float | None = Form(None), lon: float | None = Form(None),
                 uploader: str | None = Form(None)):
    name = file.filename or "upload"
    suf = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suf not in ALLOWED:
        raise HTTPException(400, f"file type {suf or '?'} not supported; use {', '.join(ALLOWED)}")
    if kind not in upload.KINDS:
        raise HTTPException(400, f"kind must be one of {upload.KINDS}")
    data = await file.read()
    if len(data) > cfg()["ingest"]["max_upload_mb"] * 1024 * 1024:
        raise HTTPException(413, f"file larger than {cfg()['ingest']['max_upload_mb']} MB")
    upload.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[-120:]
    import hashlib
    path = upload.UPLOAD_DIR / f"{hashlib.sha256(data).hexdigest()[:12]}_{safe}"
    path.write_bytes(data)
    job = upload.start(path, name, kind, (well or "").strip() or None, (country or "").strip() or None, lat, lon, uploader)
    return job


@router.get("/jobs")
def jobs():
    return sorted(upload.JOBS.values(), key=lambda j: j["created_at"], reverse=True)[:50]


@router.get("/jobs/{job_id}")
def job(job_id: str):
    j = upload.JOBS.get(job_id)
    if not j:
        raise HTTPException(404, "job not found (jobs are kept in memory until the API restarts)")
    return j
