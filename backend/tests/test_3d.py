import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DB = Path(__file__).resolve().parents[2] / "data" / "kupakosh.db"


@pytest.fixture(scope="module")
def client():
    if not DB.exists():
        pytest.skip("database not built — run `make bootstrap` first")
    from app.api import routes_3d
    from app.main import app
    # routes_3d is a new router (not yet wired into app/main.py by the lead); include it here so
    # this test exercises the real app. main.py itself is left untouched — see the final report.
    # Inserted ahead of the existing routes (and the "/" static-site mount) so it is matched first.
    if not any(getattr(r, "path", "").endswith("/scene") for r in app.router.routes):
        before = list(app.router.routes)
        app.include_router(routes_3d.router)
        added = [r for r in app.router.routes if r not in before]
        app.router.routes = added + before
    return TestClient(app)


def _any_well_with_location(client):
    rows = client.get("/api/wells", params={"limit": 200}).json()
    for w in rows:
        if w.get("lat") is not None:
            return w
    pytest.skip("no located well in the sample database")


def test_scene_shape_and_active_well_at_origin(client):
    w = _any_well_with_location(client)
    r = client.get(f"/api/wells/{w['id']}/scene")
    assert r.status_code == 200
    body = r.json()
    assert body["active_well_id"] == w["id"]
    assert body["wells"], "scene must contain at least the active well"
    active = body["wells"][0]
    assert active["is_active"] is True
    assert active["x"] == 0.0 and active["y"] == 0.0
    assert "projection" in body and "z_convention" in body
    for well in body["wells"]:
        for pt in well["trajectory"]:
            assert pt["z"] <= 0, "z must be <= 0 (down is negative)"
            assert set(pt) == {"md", "x", "y", "z"}
        for top in well["formation_tops"]:
            assert top["source_ref"]
            assert "x" in top and "y" in top
        for ev in well["events"]:
            assert ev["source_ref"]
            assert "x" in ev and "y" in ev


def test_offsets_have_distance_and_similarity(client):
    w = _any_well_with_location(client)
    body = client.get(f"/api/wells/{w['id']}/scene", params={"radius_m": 50000}).json()
    for well in body["wells"][1:]:
        assert well["is_active"] is False
        assert "distance_m" in well and "similarity" in well
        assert well["distance_m"] >= 0


def test_well_without_survey_is_flagged_assumed_vertical(client):
    w = _any_well_with_location(client)
    body = client.get(f"/api/wells/{w['id']}/scene").json()
    for well in body["wells"]:
        if well["assumed_vertical"] and well["trajectory"]:
            assert len(well["trajectory"]) == 2
            assert well["trajectory"][0]["z"] == 0.0


def test_unknown_well_404(client):
    r = client.get("/api/wells/999999999/scene")
    assert r.status_code == 404


def test_lookahead_included_when_bit_md_given(client):
    w = _any_well_with_location(client)
    r = client.get(f"/api/wells/{w['id']}/scene", params={"bit_md": 500})
    body = r.json()
    assert "lookahead" in body
    assert body["lookahead"]["bit_md_m"] == 500
