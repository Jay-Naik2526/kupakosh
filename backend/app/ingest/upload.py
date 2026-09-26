"""Upload a new report (PDF / TXT / HTML / XML) -> document + passages -> events -> episodes -> affected wiki pages.

Runs as a background job (SPEC.md §10 POST /api/ingest, §9.10 incremental updates). Only the new document's
events and the affected well's episodes are recomputed; wiki pages that change go back to draft for review.
Scanned PDFs (no text layer) are stored and flagged: OCR (Tesseract) is not installed in this build.
"""
from __future__ import annotations

import hashlib
import html
import re
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
from sqlalchemy import select

from app.config import RAW_DIR
from app.db.models import Document, Event, Passage, Well
from app.db.session import SessionLocal
from app.ingest.india_docs import _paragraphs
from app.ingest.sodir import split_sentences

UPLOAD_DIR = RAW_DIR / "uploads"
KINDS = ("DDR_PDF", "WCR_PDF", "EOWR_PDF", "WELL_HISTORY", "INCIDENT_REPORT", "OTHER")
LICENCE = "uploaded by user (not redistributed)"

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()  # one write job at a time (SQLite has a single writer)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _step(job: dict, msg: str):
    job["steps"].append({"t": _now(), "msg": msg})


def pages_of(path: Path) -> tuple[list[str], bool]:
    """Text per page, and whether the file looks scanned (PDF with no text layer)."""
    suf = path.suffix.lower()
    if suf == ".pdf":
        with pdfplumber.open(path) as pdf:
            pages = [pg.extract_text() or "" for pg in pdf.pages]
        return pages, sum(len(p.strip()) for p in pages) < 20 * max(1, len(pages))
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if suf in (".html", ".htm", ".xml"):
        raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
        raw = html.unescape(re.sub(r"<[^>]+>", "\n", raw))
    return [raw], False


def find_or_create_well(db, well: str | None, country: str | None, lat: float | None, lon: float | None) -> Well | None:
    if not well:
        return None
    if well.isdigit() and db.get(Well, int(well)):
        return db.get(Well, int(well))
    w = db.scalars(select(Well).where(Well.canonical_name == well)).first()
    if w is None:
        from app.ingest.well_ids import canonical
        w = db.scalars(select(Well).where(Well.canonical_name == canonical(well))).first()
    if w is None:
        w = Well(canonical_name=f"UP: {well}", aliases=[well], country=country, source="upload", lat=lat, lon=lon,
                 position_source="entered at upload" if lat is not None else None, purpose="added by report upload")
        db.add(w)
        db.flush()
    return w


def start(path: Path, filename: str, kind: str, well: str | None, country: str | None, lat: float | None, lon: float | None,
          uploader: str | None) -> dict:
    job = {"id": uuid.uuid4().hex[:12], "file": filename, "kind": kind, "status": "queued", "steps": [], "result": None,
           "error": None, "created_at": _now(), "uploader": uploader}
    JOBS[job["id"]] = job
    threading.Thread(target=_run, args=(job, path, kind, well, country, lat, lon), daemon=True).start()
    return job


def _run(job: dict, path: Path, kind: str, well: str | None, country: str | None, lat, lon):
    from app.engines import episodes
    from app.engines.caches import reset_all
    from app.extract import pipeline
    from app.wiki.compiler import compile_all

    with _LOCK, SessionLocal() as db:
        try:
            job["status"] = "running"
            pages, scanned = pages_of(path)
            _step(job, f"read {len(pages)} page(s)" + (" — no text layer (scanned); OCR is not installed, so nothing can be extracted" if scanned else ""))
            full = "\n".join(pages)
            sha = hashlib.sha256((full if not scanned else path.read_bytes().hex()).encode()).hexdigest()
            dup = db.scalars(select(Document).where(Document.sha256 == sha)).first()
            if dup:
                job.update(status="done", result={"duplicate_of": dup.id, "document_id": dup.id})
                _step(job, f"same content already loaded as doc:{dup.id} — nothing added")
                return
            w = find_or_create_well(db, well, country, lat, lon)
            _step(job, f"well: {w.canonical_name} (id {w.id})" if w else "no well given — text is searchable but no events are attached")
            doc = Document(well_id=w.id if w else None, kind=kind, title=f"Uploaded — {job['file']}", path=str(path.relative_to(RAW_DIR.parent)),
                           pages=len(pages), is_scanned=scanned, sha256=sha, licence=LICENCE,
                           country=(w.country if w else None) or country)
            db.add(doc)
            db.flush()
            seq = 0
            for pi, page in enumerate(pages, start=1):
                for qi, par in enumerate(_paragraphs(page), start=1):
                    sents = split_sentences(par)
                    for si, s in enumerate(sents, start=1):
                        if len(s) < 15:
                            continue
                        seq += 1
                        db.add(Passage(document_id=doc.id, well_id=w.id if w else None, seq=seq, text=s[:2000],
                                       locator=f"page {pi}, para {qi}" + (f".s{si}" if len(sents) > 1 else "")))
            db.flush()
            _step(job, f"doc:{doc.id} stored with {seq} citable sentences")
            ex = pipeline.run(db, log=lambda m: _step(job, m), doc_ids={doc.id}) if kind != "OTHER" else {"events": 0}
            new_events = db.scalars(select(Event).join(Passage, Passage.id == Event.passage_id).where(Passage.document_id == doc.id)).all()
            if w and new_events:
                episodes.run(db, log=lambda m: _step(job, m), well_ids={w.id})
            db.commit()
            try:
                from app.search import embeddings
                embeddings.build(db, log=lambda m: _step(job, m))
            except Exception as e:  # noqa: BLE001
                _step(job, f"embeddings not updated ({e!r}); keyword search still covers this document")
            reset_all()
            targets = [("well", w.id)] if w and new_events else []
            targets += [("hazard", h) for h in sorted({e.hazard for e in new_events})]
            targets += [("formation", f) for f in sorted({e.formation for e in new_events if e.formation})]
            wiki = compile_all(db, log=lambda m: _step(job, m), only=targets) if targets else {}
            db.commit()
            reset_all()
            job.update(status="done", result={"document_id": doc.id, "well_id": w.id if w else None, "passages": seq,
                                              "events": ex.get("events", 0), "scanned": scanned,
                                              "wiki_pages_back_to_review": [f"{k}:{v}" for k, v in targets], "wiki": wiki})
        except Exception as e:  # noqa: BLE001 — surfaced to the user through the job record
            db.rollback()
            job.update(status="failed", error=repr(e))
            _step(job, traceback.format_exc(limit=3))
