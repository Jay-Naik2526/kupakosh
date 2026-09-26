"""pdfplumber page text with a disk cache (data/processed/pdf_text/), so a rebuild does not re-parse hundreds of PDFs.
Cache key = file path + size + mtime; a changed file is parsed again. Errors propagate (callers count unreadable PDFs).

Pages with little or no digital text (image-only / scanned pages) are rendered at OCR_DPI and OCR'd with
Tesseract (see app.ingest.ocr). The cache key includes an "ocr" marker so a cache file written before OCR
support existed is never reused for a file that actually needed OCR — it will be re-parsed (and, if still
scanned, OCR'd) on first use after upgrading.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pdfplumber

from app.config import DATA_DIR

CACHE = DATA_DIR / "processed" / "pdf_text"

# A page with fewer digital characters than this is treated as image-only and sent to OCR.
SCANNED_CHAR_THRESHOLD = 40

# Render resolution (dots per inch) used when rasterizing a page for OCR.
OCR_DPI = 300


def _cache_key(path: Path, st) -> str:
    # "ocr2" marker: bump this suffix if the OCR pipeline behaviour changes in a way that should
    # invalidate old cache entries.
    return hashlib.sha1(f"{path.resolve()}|{st.st_size}|{int(st.st_mtime)}|ocr2".encode()).hexdigest()


def _render_page_to_image(path: Path, page_index: int):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    try:
        page = pdf[page_index]
        bitmap = page.render(scale=OCR_DPI / 72)
        return bitmap.to_pil()
    finally:
        pdf.close()


def pdf_pages_with_conf(path: Path) -> tuple[list[str], list[float | None]]:
    """Return (pages, confs). confs[i] is None for a text-layer page, or the mean OCR word
    confidence (0-100) for a page that had to be OCR'd."""
    path = Path(path)
    st = path.stat()
    key = _cache_key(path, st)
    f = CACHE / f"{key}.json"
    if f.exists():
        data = json.loads(f.read_text())
        return data["pages"], data["confs"]

    with pdfplumber.open(path) as pdf:
        raw_pages = [pg.extract_text() or "" for pg in pdf.pages]

    pages: list[str] = []
    confs: list[float | None] = []
    for i, text in enumerate(raw_pages):
        if len(text.strip()) >= SCANNED_CHAR_THRESHOLD:
            pages.append(text)
            confs.append(None)
            continue
        # Sparse/no text layer: OCR this page.
        from app.ingest.ocr import ocr_page

        try:
            image = _render_page_to_image(path, i)
            ocr_text, mean_conf = ocr_page(image)
        except Exception:  # noqa: BLE001 — e.g. a metres-long log strip Tesseract refuses: keep this page's own text
            pages.append(text)
            confs.append(None)
            continue
        pages.append(ocr_text)
        confs.append(mean_conf)

    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"pages": pages, "confs": confs}))
    return pages, confs


def pdf_pages(path: Path) -> list[str]:
    pages, _confs = pdf_pages_with_conf(path)
    return pages
