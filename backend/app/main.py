from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes, routes_brief, routes_copilot, routes_wiki, ws

app = FastAPI(title="Kupakosh API", version="0.1.0",
              description="Prototype for Oil India Limited · SIH 2026. Decision support only — the engineer decides.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (routes.router, routes_wiki.router, routes_copilot.router, routes_brief.router, ws.router):
    app.include_router(r)


@app.get("/health")
def health():
    return {"ok": True}
