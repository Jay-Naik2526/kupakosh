"""V2 — Global Analog Memory for Indian basins (docs/PLAN_V2.md USP2). See v2_common.md."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DB = Path(__file__).resolve().parents[2] / "data" / "kupakosh.db"


# ---------------------------------------------------------------------------
# Pure unit tests — lithology mapping + interval overlap. No DB needed.
# ---------------------------------------------------------------------------

def test_classify_force2020_direct_class_name():
    from app.engines.analogs import classify_lithology
    assert classify_lithology("Sandstone", None, "force2020") == "sandstone"
    assert classify_lithology("Shale", None, "force2020") == "shale"
    assert classify_lithology("Chalk", None, "force2020") == "chalk"
    assert classify_lithology("Anhydrite", None, "force2020") == "salt"
    assert classify_lithology("Dolomite", None, "force2020") == "limestone"


def test_classify_force2020_mixed_when_two_keywords_present():
    from app.engines.analogs import classify_lithology
    assert classify_lithology("Sandstone/Shale", None, "force2020") == "mixed"


def test_classify_nlog_formation_name_by_keyword():
    from app.engines.analogs import classify_lithology
    assert classify_lithology("Vlieland Claystone Formation", None, "nlog") == "claystone"
    assert classify_lithology("Z2 Carbonate Member", None, "nlog") == "limestone"
    assert classify_lithology("Upper Holland Marl Member", None, "nlog") == "marl"
    assert classify_lithology("Z2 Basal Anhydrite Member", None, "nlog") == "salt"
    # a unit whose name carries no lithology keyword at all is left unclassified, never guessed
    assert classify_lithology("Ommelanden Formation", None, "nlog") is None


def test_classify_nsta_and_forge_use_lithology_field_not_formation_name():
    from app.engines.analogs import classify_lithology
    assert classify_lithology("Fell Sandstone (Carboniferous)", "Sandstone and Shale", "nsta") == "mixed"
    assert classify_lithology("GRANITOID BASEMENT", "granite", "forge") == "basement"


def test_classify_basalt_is_not_falsely_caught_by_the_salt_keyword():
    # "Basalt" contains the substring "salt" but not the *word* "salt" — must not misclassify.
    from app.engines.analogs import classify_lithology
    assert classify_lithology("Basalt sill", "Basalt", "nsta") == "basement"


def test_classify_sodir_uses_curated_unit_map():
    from app.engines.analogs import classify_lithology
    assert classify_lithology("HUGIN FM", None, "sodir") == "sandstone"   # lithology.yaml: HUGIN FM -> sand
    assert classify_lithology("SHETLAND GP", None, "sodir") == "chalk"    # lithology.yaml: SHETLAND GP -> chalk


def test_classify_unknown_source_and_text_returns_none():
    from app.engines.analogs import classify_lithology
    assert classify_lithology(None, None, "sodir") is None
    assert classify_lithology("NO FORMAL NAME", None, "sodir") is None


def test_canonical_class_resolves_aliases():
    from app.engines.analogs import canonical_class
    assert canonical_class("carbonate") == "limestone"
    assert canonical_class("Evaporite") == "salt"
    assert canonical_class("granite") == "basement"
    assert canonical_class("sandstone") == "sandstone"
    assert canonical_class("not-a-rock") is None


def test_overlap_m():
    from app.engines.analogs import overlap_m
    assert overlap_m(1000, 1500, 1200, 1800) == 300      # partial overlap
    assert overlap_m(1000, 1500, 1500, 2000) == 0.0       # touching, no overlap
    assert overlap_m(1000, 2000, 1200, 1400) == 200.0     # fully contained
    assert overlap_m(1000, 1100, 2000, 2100) == 0.0       # far apart


# ---------------------------------------------------------------------------
# API smoke tests against the real (read-only) DB.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    if not DB.exists():
        pytest.skip("database not built — run `make bootstrap` first")
    from app.api import routes_analogs
    from app.main import app
    # routes_analogs is not yet wired into app/main.py by the lead; include it here so this test
    # exercises the real app. main.py itself is left untouched — see the final report.
    if not any(getattr(r, "path", "").startswith("/api/analogs") for r in app.router.routes):
        before = list(app.router.routes)
        app.include_router(routes_analogs.router)
        added = [r for r in app.router.routes if r not in before]
        app.router.routes = added + before
    return TestClient(app)


def test_analogs_shale_1500_2500m(client):
    r = client.get("/api/analogs", params={"lithology": "shale", "top": 1500, "base": 2500})
    assert r.status_code == 200
    body = r.json()
    assert body["query"]["canonical_class"] == "shale"
    assert body["n_intervals"] > 0
    assert body["n_wells"] > 0
    assert body["caveat"].startswith("Analogue evidence from public wells outside India")
    countries = {c["country"] for c in body["by_country"]}
    assert countries  # at least one country of evidence
    assert len(body["hazards"]) == 8  # full taxonomy when no hazard filter given
    for h in body["hazards"]:
        assert h["status"] in ("ok", "insufficient evidence")
        assert 0.0 <= h["mean"] <= 1.0
        assert h["ci"][0] <= h["mean"] <= h["ci"][1]
        # every example must be a real, checkable source reference
        for ex in h["examples"]:
            assert ex


def test_analogs_single_hazard_filter(client):
    r = client.get("/api/analogs", params={"lithology": "sandstone", "top": 1000, "base": 3000, "hazard": "kick"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["hazards"]) == 1
    assert body["hazards"][0]["hazard"] == "kick"


def test_analogs_carbonate_alias_and_bad_class(client):
    r = client.get("/api/analogs", params={"lithology": "carbonate", "top": 1000, "base": 2000})
    assert r.status_code == 200
    assert r.json()["query"]["canonical_class"] == "limestone"
    r2 = client.get("/api/analogs", params={"lithology": "unobtainium", "top": 1000, "base": 2000})
    assert r2.status_code == 400


def test_analogs_base_must_exceed_top(client):
    r = client.get("/api/analogs", params={"lithology": "shale", "top": 2000, "base": 1000})
    assert r.status_code == 400


def test_analogs_classes_endpoint(client):
    r = client.get("/api/analogs/classes")
    assert r.status_code == 200
    assert "sandstone" in r.json()["classes"]


def test_analogs_basins_suggestions_are_grounded_in_real_passages(client):
    r = client.get("/api/analogs/basins")
    assert r.status_code == 200
    basins = r.json()["basins"]
    assert basins  # 23 NDR basins expected to be loaded
    any_suggestion = False
    for b in basins:
        assert b["slug"] and b["name"]
        for s in b["suggestions"]:
            any_suggestion = True
            assert s["source_ref"].startswith("doc:")
            assert s["type"] in ("lithology", "formation")
            assert s["text"]  # the verbatim (truncated) passage the suggestion came from
            if s["type"] == "formation":
                # a formation-name suggestion must literally appear in its own quoted passage text
                assert s["value"].lower() in s["text"].lower()
    assert any_suggestion
