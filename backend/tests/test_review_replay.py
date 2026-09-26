"""Review decisions are re-applied to rebuilt events by (source_ref, hazard); unmatched ones are left alone."""
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Event, Well
from app.engines import review_replay


def test_replay(tmp_path, monkeypatch):
    eng = create_engine(f"sqlite:///{tmp_path}/r.db")
    Base.metadata.create_all(eng)
    db = sessionmaker(eng)()
    w = Well(canonical_name="T-1")
    db.add(w); db.flush()
    mk = lambda ref, hz: Event(well_id=w.id, hazard=hz, confidence=0.5, method="rule", needs_review=True, source_ref=ref)
    e1, e2, e3 = mk("doc:1#p1", "kick"), mk("doc:1#p2", "fishing"), mk("doc:1#p3", "overpressure")
    db.add_all([e1, e2, e3]); db.flush()
    log = tmp_path / "log.jsonl"
    rows = [
        {"decision": "confirm", "before": {"source_ref": "doc:1#p1", "hazard": "kick"}, "after": {"hazard": "kick", "needs_review": False, "method": "human"}},
        {"decision": "reject", "before": {"source_ref": "doc:1#p2", "hazard": "fishing"}, "after": None},
        {"decision": "relabel", "before": {"source_ref": "doc:1#p3", "hazard": "overpressure"}, "after": {"hazard": "kick", "needs_review": True, "method": "human"}},
        {"decision": "confirm", "before": {"source_ref": "doc:9#gone", "hazard": "kick"}, "after": {"needs_review": False}},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(review_replay, "LOG", log)
    n = review_replay.run(db, log=lambda *a: None)
    assert n == {"applied": 3, "stale": 1}
    evs = {e.source_ref: e for e in db.scalars(select(Event))}
    assert evs["doc:1#p1"].needs_review is False and evs["doc:1#p1"].method == "human"
    assert "doc:1#p2" not in evs
    assert evs["doc:1#p3"].hazard == "kick"
