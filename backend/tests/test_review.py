"""Tests for the human review queue (app/api/routes_review.py).

Runs entirely against a scratch, on-disk SQLite database (never data/kupakosh.db): the FastAPI
`get_db` dependency is overridden for the app, and the review audit-log path is redirected into a
tmp_path file so nothing under the repo's data/ directory is touched.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import routes_review
from app.db.models import Base, Event, Well
from app.db.session import get_db

# Built standalone (not via app.main) so this test does not depend on whether the router has been
# registered in main.py yet, and never touches the shared app / mounted frontend build.
app = FastAPI()
app.include_router(routes_review.router)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'scratch.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as db:
        norway = Well(canonical_name="15/9-F-5", country="Norway", field_name="Volve")
        india = Well(canonical_name="Baghjan-5", country="India", field_name="Baghjan")
        db.add_all([norway, india])
        db.flush()
        db.add_all([
            Event(well_id=norway.id, hazard="lost_circulation", md_m=2500.0, formation="Hugin Fm", confidence=0.4,
                  method="rule", needs_review=True, evidence_span="mud losses of 12 bbl", source_ref="doc:1#p1.s1"),
            Event(well_id=norway.id, hazard="kick", md_m=3100.0, formation="Draupne Fm", confidence=0.5,
                  method="llm", needs_review=True, evidence_span="pit gain observed", source_ref="doc:1#p2.s1"),
            Event(well_id=india.id, hazard="stuck_pipe", md_m=1800.0, formation="Barail Fm", confidence=0.3,
                  method="rule", needs_review=True, evidence_span="pipe stuck while tripping", source_ref="doc:2#p1.s1"),
            Event(well_id=norway.id, hazard="kick", md_m=2000.0, formation="Hugin Fm", confidence=0.9,
                  method="rule+llm", needs_review=False, evidence_span="already trusted", source_ref="doc:1#p3.s1"),
        ])
        db.commit()
        ids = {e.evidence_span: e.id for e in db.query(Event).all()}

    # Point the review audit log at a scratch file so the repo's data/processed/ is never written.
    monkeypatch.setattr(routes_review, "REVIEW_LOG", tmp_path / "review_log.jsonl")

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), ids, tmp_path
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_needs_review_events(client):
    c, ids, _ = client
    r = c.get("/api/review/events").json()
    assert r["total"] == 3  # the needs_review=False row is excluded
    assert {e["hazard"] for e in r["events"]} == {"lost_circulation", "kick", "stuck_pipe"}
    row = next(e for e in r["events"] if e["evidence_span"] == "mud losses of 12 bbl")
    assert row["well"] == "15/9-F-5" and row["country"] == "Norway" and row["source_ref"] == "doc:1#p1.s1"


def test_filter_by_hazard_and_country(client):
    c, ids, _ = client
    r = c.get("/api/review/events", params={"hazard": "kick"}).json()
    assert r["total"] == 1 and r["events"][0]["evidence_span"] == "pit gain observed"
    r = c.get("/api/review/events", params={"country": "India"}).json()
    assert r["total"] == 1 and r["events"][0]["well"] == "Baghjan-5"


def test_confirm_clears_review_flag_and_logs(client):
    c, ids, tmp_path = client
    eid = ids["mud losses of 12 bbl"]
    r = c.post(f"/api/review/events/{eid}", json={"decision": "confirm", "reviewer": "A. Sharma"}).json()
    assert r["ok"] and r["after"]["needs_review"] is False and r["after"]["method"] == "human"
    remaining = c.get("/api/review/events").json()
    assert eid not in [e["id"] for e in remaining["events"]]
    lines = (tmp_path / "review_log.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["reviewer"] == "A. Sharma" and row["decision"] == "confirm" and row["before"]["needs_review"] is True


def test_relabel_requires_known_taxonomy_hazard(client):
    c, ids, _ = client
    eid = ids["pit gain observed"]
    bad = c.post(f"/api/review/events/{eid}", json={"decision": "relabel", "hazard": "not_a_hazard", "reviewer": "R. Das"})
    assert bad.status_code == 422
    ok = c.post(f"/api/review/events/{eid}", json={"decision": "relabel", "hazard": "kick", "reviewer": "R. Das"}).json()
    assert ok["after"]["hazard"] == "kick"


def test_reject_deletes_event(client):
    c, ids, _ = client
    eid = ids["pipe stuck while tripping"]
    r = c.post(f"/api/review/events/{eid}", json={"decision": "reject", "reviewer": "R. Das", "note": "false positive"}).json()
    assert r["ok"] and r["after"] is None
    assert c.get(f"/api/review/events").json()["total"] == 2
    assert c.post(f"/api/review/events/{eid}", json={"decision": "confirm", "reviewer": "R. Das"}).status_code == 404


def test_reviewer_required(client):
    c, ids, _ = client
    eid = ids["mud losses of 12 bbl"]
    r = c.post(f"/api/review/events/{eid}", json={"decision": "confirm", "reviewer": "  "})
    assert r.status_code == 422


def test_unknown_decision_rejected(client):
    c, ids, _ = client
    eid = ids["mud losses of 12 bbl"]
    r = c.post(f"/api/review/events/{eid}", json={"decision": "delete", "reviewer": "R. Das"})
    assert r.status_code == 422
