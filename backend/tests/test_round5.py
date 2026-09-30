"""Round 5: accuracy work and the new features (handover note, rig hours, engineer feedback, planned-work review)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DB = Path(__file__).resolve().parents[2] / "data" / "kupakosh.db"
needs_db = pytest.mark.skipif(not DB.exists(), reason="database not built")


# --- pure logic, no DB ---------------------------------------------------------------------------------------------

def test_planned_intervention_lines_are_recognised_but_real_problems_are_not():
    import re
    from app.config import cfg
    c = cfg()["extract"]
    planned, strong = re.compile(c["planned_intervention"], re.I), re.compile(c["strong_problem"], re.I)
    is_planned = lambda t: bool(planned.search(t)) and not strong.search(t)
    assert is_planned("Made up nominal seat protector pulling tool. Released seat protector with 20 MT overpull.")
    assert is_planned("Started tractor and RIH from 3523 to 3931 m. Observed high current draw from tractor, indicating tractor stalling out.")
    # a real problem on a wireline / casing-hanger line stays trusted
    assert not is_planned("Milled casing hanger. Hole packed off, lost returns.")
    assert not is_planned("POOH with 8 1/2\" BHA. Tight spots at 519 m, pulled through with 10 MT overpull.")


def test_after_trigger_uses_the_earliest_hazard_mention():
    from app.engines.episodes import _after_trigger
    t = "Losses were controlled by pumping lost circulation materials (LCM) and reduction on ECD."
    assert _after_trigger(t, "lost_circulation").startswith(" controlled")


def test_outcome_rules_read_plain_resolution_phrases():
    from app.extract.rules import find_outcome
    assert find_outcome("Worked tight spot at 420 m, ok. Passed with no rotation - all ok.")[0] == "resolved"
    assert find_outcome("Worked string free with 20 MT overpull, string free with no excessive drag.")[0] == "resolved"
    assert find_outcome("The squeeze turned out to be not entirely successful.")[0] == "partial"
    assert find_outcome("The hole was plugged back and sidetracked from 2102 m.")[0] == "unresolved"


def test_nested_selection_candidates_are_configured():
    from app.engines.hindsight_learned import learned_cfg
    lc = learned_cfg()
    assert set(lc["candidates"]) <= {"single", "ensemble", "ensemble_ctx"} and len(lc["members"]) >= 2


def test_context_features_come_from_neighbouring_layers_only():
    from app.engines.hindsight_learned import add_context_features
    cells = [{"well_id": 1, "formation": f, "order": i, "hazard": h, "mean": m, "base": 0.01}
             for i, f in enumerate(["A", "B", "C"]) for h, m in (("kick", 0.1 * (i + 1)), ("stuck_pipe", 0.05))]
    add_context_features(cells)
    b_kick = next(c for c in cells if c["formation"] == "B" and c["hazard"] == "kick")
    assert b_kick["m_up"] == pytest.approx(0.1) and b_kick["m_dn"] == pytest.approx(0.3)
    assert b_kick["h_rank"] == 0 and 0 < b_kick["h_share"] <= 1
    a_kick = next(c for c in cells if c["formation"] == "A" and c["hazard"] == "kick")
    assert a_kick["m_up"] == -1.0  # no layer above


# --- with the database -----------------------------------------------------------------------------------------------

@needs_db
def test_handover_note_numbers_match_the_look_ahead_engine():
    from app.db.session import SessionLocal
    from app.engines import handover, lookahead
    from app.engines.context import ctx
    cx = ctx()
    wid = next(w.id for w in cx.wells.values() if w.canonical_name == "15/9-19 S")
    with SessionLocal() as db:
        note = handover.build(db, wid, 2500, "en")
        hi = handover.build(db, wid, 2500, "hi")
        la = lookahead.assess(db, wid, 2500, lookahead_m=note["lookahead_m"])
    expected = (la["alerts"] + la["notices"])[: len(note["items"])]
    assert [(i["hazard"], i["mean"]) for i in note["items"]] == [(x["hazard"], x["mean"]) for x in expected]
    for i in note["items"]:
        if i["status"] == "ok":
            assert f"{round(i['mean'] * 100)}%" in note["text"]
    assert "शिफ्ट हैंडओवर" in hi["text"] and "15/9-19 S" in hi["text"]


@needs_db
def test_rig_hours_are_line_durations_and_warned_hours_are_a_subset():
    from app.engines import righours
    s = righours.summary(force=True)
    assert s["events_timed"] > 0 and s["hours"] > 0
    assert 0 <= s["warned"]["hours"] <= s["in_test"]["hours"] <= s["hours"] + 1e-6
    assert s["warned"]["events"] <= s["in_test"]["events"] <= s["events_timed"]
    assert sum(h["hours"] for h in s["by_hazard"]) == pytest.approx(s["hours"], abs=0.5)
    for x in s["examples"]:
        assert 0 < x["hours"] <= 24 and x["source_ref"].startswith("doc:")


@needs_db
def test_engineer_feedback_teaches_estimates_but_never_becomes_a_hindsight_label():
    from fastapi.testclient import TestClient
    from app.db.models import AlertFeedback
    from app.db.session import SessionLocal
    from app.engines import context, hazard
    from app.engines.context import ctx
    from app.main import app
    cx = ctx()
    # a (well, formation, hazard) with no written record
    wid = next(w for w in sorted(cx.documented) if cx.tops.penetrated(w))
    f = sorted(cx.tops.penetrated(wid))[0]
    h = next(h for h in ("cementing_issue", "fishing", "torque_spike") if (wid, f, h) not in cx.ev_wf)
    before = hazard.base_rate(f, h)[0]
    c = TestClient(app)
    r = c.post("/api/feedback", json={"well_id": wid, "formation": f, "hazard": h, "verdict": "problem", "reviewer": "Test Runner"})
    assert r.status_code == 200 and r.json()["learned"] is True
    fid = r.json()["id"]
    try:
        cx2 = ctx()
        assert (wid, f, h) in cx2.ev_wf                 # estimates learn from it
        assert (wid, f, h) not in cx2.ev_wf_records     # the Hindsight test never scores on it
        assert hazard.base_rate(f, h)[0] >= before
        assert c.post("/api/feedback", json={"well_id": wid, "formation": f, "hazard": "nope", "verdict": "problem", "reviewer": "Test"}).status_code == 422
    finally:
        with SessionLocal() as db:
            db.query(AlertFeedback).filter(AlertFeedback.id == fid).delete()
            db.commit()
        context.reset()
        hazard.base_rate.cache_clear()
