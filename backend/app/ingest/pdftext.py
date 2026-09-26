"""pdfplumber page text with a disk cache (data/processed/pdf_text/), so a rebuild does not re-parse hundreds of PDFs.
Cache key = file path + size + mtime; a changed file is parsed again. Errors propagate (callers count unreadable PDFs)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pdfplumber

from app.config import DATA_DIR

CACHE = DATA_DIR / "processed" / "pdf_text"


def pdf_pages(path: Path) -> list[str]:
    path = Path(path)
    st = path.stat()
    key = hashlib.sha1(f"{path.resolve()}|{st.st_size}|{int(st.st_mtime)}".encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    with pdfplumber.open(path) as pdf:
        pages = [pg.extract_text() or "" for pg in pdf.pages]
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(pages))
    return pages
