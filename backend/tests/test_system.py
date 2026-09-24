"""Tests against the built database (skipped when it has not been built)."""
import pytest

from app.wiki.compiler import PageBuilder, check_citations


def test_uncited_sentence_rejected():
    pb = PageBuilder()
    pb.s("A sentence without a source.", [])
    pb.s("The top is at 1234 m.", ["doc:1#p1.s1"], facts=[999])
    pb.s("The top is at 1234 m.", ["doc:1#p1.s1"], facts=[1234])
    assert len(pb.rejected) == 2 and len(pb.refs) == 1
    assert check_citations("## Head\n\nNo citation here.\n") == ["No citation here."]
    assert check_citations("Cited. [^s1]\n\n[^s1]: doc:1#p1.s1\n") == []


def test_api_smoke(db_ready):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    s = c.get("/api/status").json()
    assert s["counts"]["wells"] > 9000 and s["counts"]["events"] > 500
    w = c.get("/api/wells", params={"q": "16B"}).json()[0]
    o = c.get(f"/api/wells/{w['id']}/offsets").json()["offsets"]
    assert o and o[0]["name"] == "16A(78)-32"
    h = c.get(f"/api/wells/{w['id']}/hazards").json()["profile"]
    assert all(p["status"] in ("ok", "insufficient_evidence") for p in h)
    # for very skewed Beta posteriors the mean can lie above the upper quantile, so only ordering is checked
    assert all(0 <= p["ci"][0] <= p["ci"][1] <= 1 and 0 <= p["mean"] <= 1 for p in h)
    ev = c.get("/api/events", params={"limit": 5}).json()
    for e in ev:
        src = c.get("/api/source", params={"ref": e["source_ref"]}).json()
        assert src["found"] and e["evidence"] in src["text"]  # every event traces to its verbatim line
    r = c.post("/api/copilot", json={"question": "What is the friction angle of the Draupne shale?"}).json()
    assert r["refused"] and r["answer"].startswith("No evidence found in the records.")


def test_review_creates_commit_and_noting(db_ready):
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    slug = "hazards/fishing"
    before = c.get(f"/api/wiki/{slug}/noting").json()
    hist0 = c.get(f"/api/wiki/{slug}/history").json()
    bad = c.post(f"/api/wiki/{slug}/review", json={"action": "edit", "reviewer": "test", "content": "Uncited line.\n"})
    assert bad.status_code == 422
    r = c.post(f"/api/wiki/{slug}/review", json={"action": "return", "reviewer": "pytest", "role": "test", "note": "test run"}).json()
    assert r["status"] == "returned"
    assert len(c.get(f"/api/wiki/{slug}/noting").json()) == len(before) + 1
    assert len(c.get(f"/api/wiki/{slug}/history").json()) == len(hist0) + 1
