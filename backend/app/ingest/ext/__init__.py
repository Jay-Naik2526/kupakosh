"""Plug-in ingesters for additional public data sources (one module per source).

Contract (every module in this package):
    SOURCE: dict  = {"name", "country", "url", "licence", "raw_dir"}   # raw_dir relative to data/raw
    def ingest(db: Session, log=print) -> dict                           # returns counts; must not commit

Rules: only real downloaded records (no invented values); every Well gets `country`, `source`, and
`position_source` when lat/lon are set; every Document gets `url` + `licence`; text is split into Passages
so events can be extracted and cited. Modules are discovered and run by scripts/bootstrap.py.
"""
from __future__ import annotations

import importlib
import pkgutil


def modules(log=print):
    out = []
    for m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if m.name.startswith("_"):
            continue
        try:
            out.append(importlib.import_module(f"{__name__}.{m.name}"))
        except Exception as e:  # noqa: BLE001 — one broken plug-in must not stop the others
            log(f"ext {m.name}: import FAILED {e!r}")
    return out
