"""Tests for the compact well-map endpoints (app/api/routes_geo.py, task V4).

Builds a tiny standalone FastAPI app with just this router (mirrors tests/test_review.py's pattern) so this
file doesn't depend on the lead having wired routes_geo into app.main yet. Runs against the real
data/kupakosh.db (read-only) via the shared db_ready fixture.
"""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_geo

app = FastAPI()
app.include_router(routes_geo.router)
client = TestClient(app)


def test_geo_wells_shape(db_ready):
    r = client.get("/api/geo/wells")
    assert r.status_code == 200
    body = r.json()
    assert body["fields"] == routes_geo.GEO_FIELDS
    assert body["n"] == len(body["rows"]) > 0
    assert set(body["kinds"]) >= {"well", "block_aggregate", "field_centroid"}
    row = body["rows"][0]
    assert len(row) == len(routes_geo.GEO_FIELDS)
    wid, name, cidx, lat, lon, has_events, n_events, documented, kidx = row
    assert isinstance(wid, int) and isinstance(name, str)
    assert 0 <= cidx < len(body["countries"])
    assert -90 <= lat <= 90 and -180 <= lon <= 180
    assert has_events in (0, 1) and documented in (0, 1)
    assert n_events >= 0
    assert 0 <= kidx < len(body["kinds"])
    # has_events must agree with n_events (has_events is just n_events > 0, kept as a separate flag for the UI)
    assert has_events == (1 if n_events > 0 else 0)


def test_geo_wells_country_filter(db_ready):
    all_rows = client.get("/api/geo/wells").json()
    countries = all_rows["countries"]
    some_country = next(c for c in countries if c != "unknown")
    filtered = client.get("/api/geo/wells", params={"country": some_country}).json()
    assert filtered["n"] > 0
    assert filtered["n"] < all_rows["n"]
    for r in filtered["rows"]:
        assert filtered["countries"][r[2]] == some_country


def test_geo_wells_payload_under_budget(db_ready):
    r = client.get("/api/geo/wells")
    size = len(r.content)
    # ~6 MB uncompressed budget from the task spec; GZipMiddleware (to be added in main.py) compresses this
    # further in transit — this test only guards the uncompressed size doesn't balloon.
    assert size < 8 * 1024 * 1024, f"payload is {size} bytes, expected well under 8 MB uncompressed"


def test_geo_basins_shape(db_ready):
    r = client.get("/api/geo/basins")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    for f in body["features"]:
        assert f["geometry"]["type"] == "Polygon"
        ring = f["geometry"]["coordinates"][0]
        assert len(ring) == 5 and ring[0] == ring[-1]
        assert f["properties"]["name"] and f["properties"]["url"]


def test_geo_wells_cache_reset(db_ready):
    routes_geo._rows()  # populate cache
    routes_geo.reset_cache()
    assert routes_geo._rows.cache_info().currsize == 0
