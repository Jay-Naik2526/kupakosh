from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes, routes_brief, routes_copilot, routes_ingest, routes_wiki, ws

app = FastAPI(title="Kupakosh API", version="0.1.0",
              description="Prototype for Oil India Limited · SIH 2026. Decision support only — the engineer decides.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (routes.router, routes_ingest.router, routes_wiki.router, routes_copilot.router, routes_brief.router, ws.router):
    app.include_router(r)


@app.get("/health")
def health():
    return {"ok": True}


# Built website (frontend: `KK_EXPORT=1 npm run build` -> frontend/out). Serving it here puts the site, the API and the
# replay WebSocket on ONE address, so a single shared link (LAN IP or tunnel) works for teammates.
mimetypes.add_type("text/javascript", ".mjs")  # MapLibre worker module (strict MIME check for module scripts)
SITE = Path(__file__).resolve().parents[2] / "frontend" / "out"
if SITE.exists():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
