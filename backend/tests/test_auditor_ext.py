"""Tests for the auditor extensions (SPEC.md §9.9): R5 (summary vs daily reports), and the widened
R2/R3 (casing shoe / formation top) coverage beyond Sodir well-history text.

Runs entirely against a scratch, in-memory-style on-disk SQLite database (never data/kupakosh.db).
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import AuditFlag, Base, CasingString, Document, Event, FormationTop, Passage, Well
from app.engines import auditor


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'scratch.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        yield s


def _event(well_id, doc_id, hazard, md_m, locator="p1.s1", text="synthetic evidence"):
    return Event(well_id=well_id, hazard=hazard, md_m=md_m, confidence=0.8, method="rule",
                 evidence_span=text, source_ref=f"doc:{doc_id}#{locator}")


def test_r5_flags_event_missing_from_daily_reports_and_reverse(db):
    """Synthetic well with one EOWR (summary) doc and one DDR doc: a lost-circulation event only in
    the summary report, a kick event only in the DDR, and a stuck-pipe event in both (should not
    flag). No well in the current real dataset has both a summary doc and a DDR_PDF (checked against
    data/kupakosh.db before writing this rule), so this synthetic fixture is the only way to exercise
    R5's matching logic; it is expected to produce 0 flags on the real bootstrap data."""
    w = Well(canonical_name="TEST-1", country="Netherlands", source="nlog")
    db.add(w)
    db.flush()
    eowr = Document(well_id=w.id, kind="EOWR_PDF", report_date=None)
    ddr = Document(well_id=w.id, kind="DDR_PDF", report_date=None)
    db.add_all([eowr, ddr])
    db.flush()
    p_summary = Passage(document_id=eowr.id, well_id=w.id, locator="p1.s1", seq=1, text="Lost circulation at 2500 m.")
    p_summary2 = Passage(document_id=eowr.id, well_id=w.id, locator="p1.s2", seq=2, text="Stuck pipe at 3000 m.")
    p_ddr = Passage(document_id=ddr.id, well_id=w.id, locator="p1.s1", seq=1, text="Kick observed at 1800 m.")
    p_ddr2 = Passage(document_id=ddr.id, well_id=w.id, locator="p1.s2", seq=2, text="Stuck pipe at 3005 m.")
    db.add_all([p_summary, p_summary2, p_ddr, p_ddr2])
    db.flush()
    db.add_all([
        Event(well_id=w.id, passage_id=p_summary.id, hazard="lost_circulation", md_m=2500.0, confidence=0.8,
              method="rule", evidence_span="Lost circulation at 2500 m.", source_ref=f"doc:{eowr.id}#p1.s1"),
        Event(well_id=w.id, passage_id=p_summary2.id, hazard="stuck_pipe", md_m=3000.0, confidence=0.8,
              method="rule", evidence_span="Stuck pipe at 3000 m.", source_ref=f"doc:{eowr.id}#p1.s2"),
        Event(well_id=w.id, passage_id=p_ddr.id, hazard="kick", md_m=1800.0, confidence=0.8,
              method="rule", evidence_span="Kick observed at 1800 m.", source_ref=f"doc:{ddr.id}#p1.s1"),
        Event(well_id=w.id, passage_id=p_ddr2.id, hazard="stuck_pipe", md_m=3005.0, confidence=0.8,
              method="rule", evidence_span="Stuck pipe at 3005 m.", source_ref=f"doc:{ddr.id}#p1.s2"),
    ])
    db.commit()

    counts = auditor.run(db)
    assert counts.get("R5_summary_vs_daily") == 2

    flags = db.query(AuditFlag).filter(AuditFlag.rule == "R5_summary_vs_daily").all()
    assert len(flags) == 2
    by_hazard = {f.claim_a.split(" reports ")[1].split(" at ")[0]: f for f in flags}
    assert "lost_circulation" in by_hazard and "kick" in by_hazard
    # the stuck_pipe event (3000 vs 3005, within the 30 m default tolerance) must NOT be flagged
    assert not any("stuck_pipe" in f.claim_a for f in flags)

    lc = by_hazard["lost_circulation"]
    assert lc.ref_a == f"doc:{eowr.id}#p1.s1"
    assert lc.ref_b == f"doc:{ddr.id}#header"
    assert lc.severity == "medium"

    kick = by_hazard["kick"]
    assert kick.ref_a == f"doc:{ddr.id}#p1.s1"
    assert kick.ref_b == f"doc:{eowr.id}#header"
    assert kick.severity == "low"


def test_r5_zero_flags_when_only_one_report_kind_exists(db):
    """A well with only a DDR_PDF (no summary document) must never be entered into R5 at all."""
    w = Well(canonical_name="TEST-2", country="Norway", source="sodir")
    db.add(w)
    db.flush()
    ddr = Document(well_id=w.id, kind="DDR_PDF")
    db.add(ddr)
    db.flush()
    p = Passage(document_id=ddr.id, well_id=w.id, locator="p1.s1", seq=1, text="Kick at 1800 m.")
    db.add(p)
    db.flush()
    db.add(Event(well_id=w.id, passage_id=p.id, hazard="kick", md_m=1800.0, confidence=0.8,
                 method="rule", evidence_span="Kick at 1800 m.", source_ref=f"doc:{ddr.id}#p1.s1"))
    db.commit()

    counts = auditor.run(db)
    assert counts.get("R5_summary_vs_daily", 0) == 0


def test_r2_casing_shoe_covers_wcr_pdf_text_not_just_well_history(db):
    """R2 must now also compare casing text mentions in WCR_PDF (e.g. Australia/gsq) — previously it
    only looked at WELL_HISTORY (Sodir) documents."""
    w = Well(canonical_name="TEST-AU-1", country="Australia", source="gsq")
    db.add(w)
    db.flush()
    wcr = Document(well_id=w.id, kind="WCR_PDF")
    db.add(wcr)
    db.flush()
    p = Passage(document_id=wcr.id, well_id=w.id, locator="page 3, para 1.s1", seq=1,
                text='Ran 9 5/8" casing and landed it off with shoe at 300 m.')
    db.add(p)
    db.add(CasingString(well_id=w.id, casing_type="production", od_in=9.625, shoe_md_m=260.0,
                         source_ref=f"doc:{wcr.id}#casing:1"))
    db.commit()

    counts = auditor.run(db)
    assert counts.get("R2_casing_shoe") == 1
    flag = db.query(AuditFlag).filter(AuditFlag.rule == "R2_casing_shoe").one()
    assert flag.ref_a == f"doc:{wcr.id}#page 3, para 1.s1"
    assert flag.ref_b == f"doc:{wcr.id}#casing:1"
    assert "well completion report text" in flag.claim_a
    assert "GSQ" in flag.claim_b


def test_r2_no_flag_when_text_and_table_agree_within_tolerance(db):
    w = Well(canonical_name="TEST-AU-2", country="Australia", source="gsq")
    db.add(w)
    db.flush()
    wcr = Document(well_id=w.id, kind="WCR_PDF")
    db.add(wcr)
    db.flush()
    p = Passage(document_id=wcr.id, well_id=w.id, locator="p1.s1", seq=1,
                text='Ran 9 5/8" casing and landed it off with shoe at 260 m.')
    db.add(p)
    db.add(CasingString(well_id=w.id, casing_type="production", od_in=9.625, shoe_md_m=265.0,
                         source_ref=f"doc:{wcr.id}#casing:1"))
    db.commit()

    counts = auditor.run(db)
    assert counts.get("R2_casing_shoe", 0) == 0


def test_r3_formation_top_covers_nlog_source_and_eowr_text(db):
    """R3 must now also compare formation-top text mentions in EOWR_PDF against nlog-sourced tops —
    previously it only compared WELL_HISTORY text against sodir tops."""
    w = Well(canonical_name="TEST-NL-1", country="Netherlands", source="nlog")
    db.add(w)
    db.flush()
    eowr = Document(well_id=w.id, kind="EOWR_PDF")
    db.add(eowr)
    db.flush()
    p = Passage(document_id=eowr.id, well_id=w.id, locator="page 5, para 2.s1", seq=1,
                text="The top Rijnland Formation was at 1200 m.")
    db.add(p)
    db.add(FormationTop(well_id=w.id, formation="RIJNLAND FM", top_md_m=1150.0, source="nlog",
                         source_ref="nlog:table:RIJNLAND"))
    db.commit()

    counts = auditor.run(db)
    assert counts.get("R3_formation_top") == 1
    flag = db.query(AuditFlag).filter(AuditFlag.rule == "R3_formation_top").one()
    assert flag.ref_a == f"doc:{eowr.id}#page 5, para 2.s1"
    assert flag.ref_b == "nlog:table:RIJNLAND"
    assert "end-of-well report text" in flag.claim_a
    assert "nlog/NLOG" in flag.claim_b
