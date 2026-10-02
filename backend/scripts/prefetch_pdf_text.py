"""Read (and OCR where needed) many PDFs in parallel into the text cache (data/processed/pdf_text), so a later
ingest finds every file already read. Usage: python -m scripts.prefetch_pdf_text <plan.json|dir> [--workers N] [--max-ocr-pages N]"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def _one(path: str, cap: int | None) -> tuple[str, int, int]:
    from app.ingest.pdftext import pdf_pages_with_conf
    try:
        pages, confs = pdf_pages_with_conf(Path(path), max_ocr_pages=cap)
        return path, len(pages), sum(c is not None for c in confs)
    except Exception as e:  # noqa: BLE001 - an unreadable file must not stop the batch
        return path, -1, 0


def main() -> None:
    a = sys.argv[1:]
    src = Path(a[0])
    workers = int(a[a.index("--workers") + 1]) if "--workers" in a else 6
    cap = int(a[a.index("--max-ocr-pages") + 1]) if "--max-ocr-pages" in a else None
    if src.suffix == ".json":
        from scripts.add_nlog_reports import REPORTS, _sanitise
        paths = [str(REPORTS / f"{_sanitise(x['boreholeName'])}__{x['assetBfileDbk']}.pdf") for x in json.loads(src.read_text())]
    else:
        paths = [str(p) for p in sorted(src.glob("*.pdf"))]
    paths = [p for p in paths if Path(p).exists()]
    t0, done, ocr_pages, bad = time.time(), 0, 0, 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_one, p, cap) for p in paths]
        for f in as_completed(futs):
            p, n, o = f.result()
            done += 1
            ocr_pages += o
            bad += n < 0
            if done % 20 == 0 or done == len(paths):
                print(f"prefetch: {done}/{len(paths)} files, {ocr_pages} OCR pages, {bad} unreadable, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
