"""V1 — Hindsight Test (docs/PLAN_V2.md USP1). See v2_common.md for shared conventions."""
from app.config import cfg
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DB = Path(__file__).resolve().parents[2] / "data" / "kupakosh.db"


# ---------------------------------------------------------------------------
# Synthetic unit tests of the pure matching/lift logic — no DB needed.
# ---------------------------------------------------------------------------

def test_match_event_forewarned_with_correct_lead():
    from app.engines.hindsight import match_event

    alerts = [{"formation": "HUGIN FM", "hazard": "lost_circulation", "alert_md_m": 1850.0, "mean": 0.55, "n_eff": 6.0}]
    idx = {(a["formation"], a["hazard"]): a for a in alerts}

    forewarned, lead_m, alert = match_event(idx, "HUGIN FM", "lost_circulation", 2000.0)
    assert forewarned is True
    assert lead_m == 150.0
    assert alert["alert_md_m"] == 1850.0


def test_match_event_missed_wrong_formation_or_hazard():
    from app.engines.hindsight import match_event

    alerts = [{"formation": "HUGIN FM", "hazard": "lost_circulation", "alert_md_m": 1850.0}]
    idx = {(a["formation"], a["hazard"]): a for a in alerts}

    fw, lead, a = match_event(idx, "DRAUPNE FM", "lost_circulation", 2000.0)
    assert fw is False and lead is None and a is None
    fw, lead, a = match_event(idx, "HUGIN FM", "kick", 2000.0)
    assert fw is False and lead is None and a is None
    fw, lead, a = match_event(idx, None, "lost_circulation", 2000.0)
    assert fw is False and lead is None and a is None


def test_match_event_no_alert_at_all_is_missed():
    from app.engines.hindsight import match_event
    fw, lead, a = match_event({}, "HUGIN FM", "kick", 100.0)
    assert fw is False and lead is None and a is None


def test_aggregate_rolls_up_events_and_median_lead():
    from app.engines.hindsight import aggregate

    rows = [
        {"events": 2, "forewarned": 1, "missed": 1, "leads_m": [100.0], "alerts": 2, "alerts_with_event": 1, "baseline_forewarned": 1},
        {"events": 3, "forewarned": 2, "missed": 1, "leads_m": [50.0, 150.0], "alerts": 1, "alerts_with_event": 1, "baseline_forewarned": 0},
    ]
    agg = aggregate(rows)
    assert agg["events"] == 5
    assert agg["forewarned"] == 3
    assert agg["missed"] == 2
    assert agg["forewarned_share"] == pytest.approx(3 / 5)
    assert agg["median_lead_m"] == 100.0
    assert agg["alerts"] == 3
    assert agg["alerts_with_event"] == 2
    assert agg["alerts_without_record"] == 1
    assert agg["baseline_forewarned"] == 1
    assert agg["baseline_forewarned_share"] == pytest.approx(1 / 5)


def test_aggregate_handles_no_events_or_alerts():
    from app.engines.hindsight import aggregate
    agg = aggregate([{"events": 0, "forewarned": 0, "missed": 0, "leads_m": [], "alerts": 0, "alerts_with_event": 0, "baseline_forewarned": 0}])
    assert agg["forewarned_share"] is None
    assert agg["median_lead_m"] is None
    assert agg["alerts_with_event_share"] is None
    assert agg["baseline_forewarned_share"] is None


def _cell(y, well_id=1, formation="F", hazard="kick", base=0.1):
    return {"well_id": well_id, "formation": formation, "hazard": hazard, "y": y, "base": base}


def test_wilson_ci_bounds_and_shrinks_with_n():
    from app.engines.hindsight import wilson_ci
    lo, hi = wilson_ci(5, 10)
    assert 0.0 <= lo <= 0.5 <= hi <= 1.0
    lo_small, hi_small = wilson_ci(5, 10)
    lo_big, hi_big = wilson_ci(500, 1000)
    assert (hi_big - lo_big) < (hi_small - lo_small)  # more data -> tighter interval, same point estimate


def test_lift_report_detects_real_lift():
    from app.engines.hindsight import lift_report
    # flagged cells: mostly positive; unflagged: mostly negative -> clear lift, CI should exclude 1
    cells = [{"flag": True, "y": 1, "well_id": i, "formation": "F", "hazard": "kick", "base": 0.1} for i in range(40)]
    cells += [{"flag": True, "y": 0, "well_id": i, "formation": "F", "hazard": "kick", "base": 0.1} for i in range(10)]
    cells += [{"flag": False, "y": 0, "well_id": i, "formation": "F", "hazard": "kick", "base": 0.1} for i in range(190)]
    cells += [{"flag": False, "y": 1, "well_id": i, "formation": "F", "hazard": "kick", "base": 0.1} for i in range(10)]
    r = lift_report(cells, "flag")
    assert r["n_flagged"] == 50 and r["n_unflagged"] == 200
    assert r["rate_flagged"] == pytest.approx(0.8)
    assert r["rate_unflagged"] == pytest.approx(0.05)
    assert r["lift"] == pytest.approx(16.0)
    assert r["no_measured_lift_yet"] is False
    assert "no measured lift yet" not in r["headline"]


def test_lift_report_says_no_measured_lift_when_ci_spans_one():
    from app.engines.hindsight import lift_report
    # small, noisy sample where flagged and unflagged rates are close -> CI should span 1
    cells = [{"flag": True, "y": 1, "well_id": 1, "formation": "F", "hazard": "kick", "base": 0.1}]
    cells += [{"flag": True, "y": 0, "well_id": 2, "formation": "F", "hazard": "kick", "base": 0.1}]
    cells += [{"flag": False, "y": 1, "well_id": 3, "formation": "F", "hazard": "kick", "base": 0.1}]
    cells += [{"flag": False, "y": 0, "well_id": 4, "formation": "F", "hazard": "kick", "base": 0.1}]
    r = lift_report(cells, "flag")
    assert r["no_measured_lift_yet"] is True
    assert r["headline"] == "no measured lift yet"


def test_lift_report_no_flags_is_explicit():
    from app.engines.hindsight import lift_report
    cells = [{"flag": False, "y": 0, "well_id": 1, "formation": "F", "hazard": "kick", "base": 0.1}]
    r = lift_report(cells, "flag")
    assert r["n_flagged"] == 0
    assert r["no_measured_lift_yet"] is True
    assert r["note"] == "no cells were flagged by this rule"


def test_baseline_lift_report_picks_top_k_by_base_rate():
    from app.engines.hindsight import baseline_lift_report
    cells = [
        {"well_id": 1, "formation": "A", "hazard": "kick", "base": 0.9, "y": 1},
        {"well_id": 2, "formation": "B", "hazard": "kick", "base": 0.8, "y": 1},
        {"well_id": 3, "formation": "C", "hazard": "kick", "base": 0.1, "y": 0},
        {"well_id": 4, "formation": "D", "hazard": "kick", "base": 0.05, "y": 0},
    ]
    r = baseline_lift_report(cells, k=2)
    assert r["n_flagged"] == 2
    assert r["rate_flagged"] == pytest.approx(1.0)  # the two highest-base-rate cells are exactly the two positives here
    assert r["rate_unflagged"] == pytest.approx(0.0)


def test_baseline_lift_report_zero_k():
    from app.engines.hindsight import baseline_lift_report
    r = baseline_lift_report([_cell(1)], k=0)
    assert r["n_flagged"] == 0
    assert r["no_measured_lift_yet"] is True


# ---------------------------------------------------------------------------
# API smoke test against the real (read-only) DB. main.py now wires routes_hindsight in
# directly (per the lead), but we still include it defensively in case this test runs
# against an older main.py — the include is a no-op if the routes already exist.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    if not DB.exists():
        pytest.skip("database not built — run `make bootstrap` first")
    from app.api import routes_hindsight
    from app.main import app
    if not any(getattr(r, "path", "").startswith("/api/hindsight") for r in app.router.routes):
        before = list(app.router.routes)
        app.include_router(routes_hindsight.router)
        added = [r for r in app.router.routes if r not in before]
        app.router.routes = added + before
    return TestClient(app)


def _forge_16b_id(client) -> int:
    rows = client.get("/api/wells", params={"q": "16B(78)-32"}).json()
    for w in rows:
        if w["name"] == "16B(78)-32":
            return w["id"]
    pytest.skip("FORGE well 16B(78)-32 not present in this database")


def test_hindsight_well_16b_is_a_blind_self_consistent_replay(client):
    wid = _forge_16b_id(client)
    r = client.get(f"/api/hindsight/{wid}")
    assert r.status_code == 200
    body = r.json()
    assert body["well"]["id"] == wid
    assert body["well"]["name"] == "16B(78)-32"
    assert body["alert_mode"] in ("elevated", "absolute")
    assert "formations" in body and "alerts" in body and "events" in body
    s = body["summary"]
    assert s["forewarned"] + s["missed"] == s["events"]
    assert s["alerts_with_event"] + s["alerts_without_record"] == s["alerts"]
    assert s["alerts_with_event"] <= s["alerts"]
    for a in body["alerts"]:
        assert "evidence" in a
        for ev in a["evidence"]:
            assert ev["well_id"] != wid  # blind replay: the well never appears in its own evidence
            for evt in ev["events"]:
                assert evt["source_ref"]
    for e in body["events"]:
        assert e["source_ref"]


def test_hindsight_unknown_well_404(client):
    assert client.get("/api/hindsight/999999999").status_code == 404


def test_hindsight_summary_reports_lift_with_counts_and_ci(client):
    r = client.get("/api/hindsight/summary", params={"max_wells": 80})
    assert r.status_code == 200
    body = r.json()
    assert body["n_testable"] <= body["n_candidates"] <= 80
    assert body["alert_mode_config"] == cfg()["hindsight"]["alert_mode"]
    m = body["lift"]["model"]
    b = body["lift"]["baseline"]
    assert m["n_flagged"] + m["n_unflagged"] == body["n_cells"]
    assert b["n_flagged"] == m["n_flagged"]  # fair baseline: same number of flags as the model
    if m["n_flagged"]:
        assert m["rate_flagged_ci"][0] <= m["rate_flagged"] <= m["rate_flagged_ci"][1]
    if m["n_unflagged"]:
        assert m["rate_unflagged_ci"][0] <= m["rate_unflagged"] <= m["rate_unflagged_ci"][1]
    assert isinstance(m["headline"], str) and m["headline"]
    assert body["headline"] == m["headline"]
    # secondary metrics still present
    f = body["forewarned"]
    if f["events"]:
        assert f["forewarned"] + f["missed"] == f["events"]


def test_hindsight_method_text_is_honest_about_no_recorded_event(client):
    body = client.get("/api/hindsight/summary", params={"max_wells": 40}).json()
    assert "no recorded event" in body["method"].lower()
    assert "not a false alarm" in body["method"].lower() or "not false alarm" in body["method"].lower().replace("a false", "false")


def test_hindsight_no_measured_lift_yet_wording_when_ci_spans_one():
    """Direct check on the honesty rule (requirement 4), independent of what the live DB happens to show."""
    from app.engines.hindsight import _lift_core
    flagged = [{"y": 1}, {"y": 0}]
    unflagged = [{"y": 1}, {"y": 0}]
    r = _lift_core(flagged, unflagged)
    assert r["no_measured_lift_yet"] is True
    assert r["headline"] == "no measured lift yet"


def test_hindsight_by_source_stratification_present(client):
    body = client.get("/api/hindsight/summary", params={"max_wells": 200}).json()
    assert "by_source" in body and "by_country" in body
    for src, strat in body["by_source"].items():
        assert strat["n_wells"] >= 0
        assert "lift" in strat and "baseline" in strat and "forewarned" in strat
        assert strat["lift"]["n_flagged"] + strat["lift"]["n_unflagged"] == strat["n_cells"]


def test_hindsight_summary_source_filter_matches_stratum(client):
    full = client.get("/api/hindsight/summary", params={"max_wells": 200}).json()
    sources = [s for s, strat in full["by_source"].items() if strat["n_wells"] > 0]
    if not sources:
        pytest.skip("no source with testable wells in this sample")
    src = sources[0]
    r = client.get("/api/hindsight/summary", params={"max_wells": 200, "source": src})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == src
    assert body["n_cells"] == full["by_source"][src]["n_cells"]


def test_hindsight_wells_list_filters_by_source(client):
    rows = client.get("/api/hindsight/wells", params={"max_wells": 200}).json()
    if not rows:
        pytest.skip("no testable wells in this sample")
    src = rows[0]["source"]
    filtered = client.get("/api/hindsight/wells", params={"max_wells": 200, "source": src}).json()
    assert filtered and all(r["source"] == src for r in filtered)


def test_hindsight_summary_unknown_source_404(client):
    assert client.get("/api/hindsight/summary", params={"max_wells": 40, "source": "not-a-real-source"}).status_code == 404
