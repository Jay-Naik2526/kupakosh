from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (routes, routes_3d, routes_analogs, routes_brief, routes_copilot, routes_geo, routes_hindsight, routes_ingest, routes_review,
                     routes_wiki, ws)

app = FastAPI(title="Kupakosh API", version="0.1.0",
              description="Prototype for Oil India Limited · SIH 2026. Decision support only — the engineer decides.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)  # large JSON (e.g. /api/geo/wells ~5 MB -> ~0.8 MB)
for r in (routes.router, routes_3d.router, routes_geo.router, routes_analogs.router, routes_hindsight.router, routes_ingest.router, routes_review.router, routes_wiki.router, routes_copilot.router, routes_brief.router, ws.router):
    app.include_router(r)


@app.on_event("startup")
def _warm():
    """Build the shared in-memory context before serving (first requests would otherwise all wait on it)."""
    import threading
    from app.engines.context import ctx
    threading.Thread(target=ctx, daemon=True).start()


@app.get("/health")
def health():
    return {"ok": True}


# Built website (frontend: `KK_EXPORT=1 npm run build` -> frontend/out). Serving it here puts the site, the API and the
# replay WebSocket on ONE address, so a single shared link (LAN IP or tunnel) works for teammates.
mimetypes.add_type("text/javascript", ".mjs")  # MapLibre worker module (strict MIME check for module scripts)
SITE = Path(__file__).resolve().parents[2] / "frontend" / "out"
if SITE.exists():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
