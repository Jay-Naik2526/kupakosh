"""Live rig feed (WITSML / WITS0), "Verify this number" recounts, and the server reliability scripts."""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "kupakosh.db"
needs_db = pytest.mark.skipif(not DB.exists(), reason="database not built")


# --- parsers, no DB --------------------------------------------------------------------------------------------------

def _rows(n=3):
    return [{"t": datetime(2024, 1, 1, 0, 0, i, tzinfo=timezone.utc), "md_m": 1500 + i * 0.1, "bit_md_m": 1500 + i * 0.1, "rop": 20.0,
             "wob": 30.0, "rpm": 80.0, "torque": 12.5, "spp": 2500.0, "flow_in": 600.0, "pit_vol": 400.5, "hookload": 200.0} for i in range(n)]


def test_witsml_round_trip_keeps_every_channel_and_value():
    from app.ingest.witsml_stream import parse_witsml_log, to_witsml_log
    d = parse_witsml_log(to_witsml_log("16B", _rows()))
    assert d["well"] == "16B" and d["skipped"] == [] and len(d["samples"]) == 3
    s = d["samples"][2]
    assert s["t"] == "2024-01-01T00:00:02+00:00"
    assert s["md_m"] == pytest.approx(1500.2) and s["torque"] == 12.5 and s["pit_vol"] == 400.5 and s["hookload"] == 200.0


def test_witsml_converts_foreign_units_and_reports_unknown_curves():
    from app.ingest.witsml_stream import parse_witsml_log
    x = ('<logs xmlns="http://www.witsml.org/schemas/1series"><log><nameWell>X</nameWell><logData>'
         '<mnemonicList>TIME,DMEA,TQA,SPPA,TVA,GASX</mnemonicList><unitList>s,ft,kN.m,bar,m3,%</unitList>'
         '<data>2024-01-01T00:00:00Z,1000,10,100,1,3</data></logData></log></logs>')
    d = parse_witsml_log(x)
    s = d["samples"][0]
    assert s["md_m"] == pytest.approx(304.8) and s["torque"] == pytest.approx(7.37562) and s["spp"] == pytest.approx(1450.38)
    assert s["pit_vol"] == pytest.approx(6.2898)
    assert "GASX" in d["skipped"]  # never guessed


def test_unknown_unit_is_dropped_not_guessed():
    from app.ingest.witsml_stream import parse_witsml_log
    d = parse_witsml_log('<logs><log><logData><mnemonicList>TIME,DEPT,TQA</mnemonicList><unitList>s,m,furlong</unitList>'
                         '<data>2024-01-01T00:00:00Z,10,5</data></logData></log></logs>')
    assert "torque" not in d["samples"][0] and any("furlong" in k for k in d["skipped"])


def test_witsml_rejects_dtd_and_garbage():
    from app.ingest.witsml_stream import FeedError, parse_witsml_log
    with pytest.raises(FeedError):
        parse_witsml_log('<!DOCTYPE x [<!ENTITY a "b">]><logs/>')
    with pytest.raises(FeedError):
        parse_witsml_log("not xml")
    with pytest.raises(FeedError):
        parse_witsml_log("<logs></logs>")


def test_wits0_records_metric_and_imperial():
    from app.ingest.witsml_stream import FeedError, parse_wits0
    rec = "&&\n0105240101\n0106120000\n01101000.0\n01181.0\n0121100\n!!\n"
    m = parse_wits0(rec, "metric")["samples"][0]
    assert m["t"] == "2024-01-01T12:00:00+00:00" and m["md_m"] == 1000.0
    assert m["torque"] == pytest.approx(0.737562) and m["spp"] == pytest.approx(14.5038)
    i = parse_wits0(rec, "imperial")["samples"][0]
    assert i["md_m"] == pytest.approx(304.8) and i["torque"] == 1.0 and i["spp"] == 100.0
    with pytest.raises(FeedError):
        parse_wits0("no records here")


# --- API (needs the database) ----------------------------------------------------------------------------------------

@needs_db
def test_live_post_needs_the_token_and_reaches_viewers():
    from fastapi.testclient import TestClient

    from app.engines import livefeed as lf
    from app.ingest.witsml_stream import to_witsml_log
    from app.main import app
    from sqlalchemy import select
    from app.db.models import RealtimeSample
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        wid = db.scalars(select(RealtimeSample.well_id).limit(1)).first()
    c = TestClient(app)
    doc = to_witsml_log("t", _rows(5))
    assert c.post(f"/api/live/{wid}/witsml", content=doc).status_code == 401
    assert c.post(f"/api/live/{wid}/witsml", content=doc, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.post("/api/live/999999999/witsml", content=doc, headers={"Authorization": f"Bearer {lf.feed_token()}"}).status_code == 404
    with c.websocket_connect(f"/ws/live/{wid}") as ws:
        assert ws.receive_json()["mode"] == "LIVE"
        r = c.post(f"/api/live/{wid}/witsml", content=doc, headers={"Authorization": f"Bearer {lf.feed_token()}", "X-Feed-Source": "pytest"})
        assert r.status_code == 200 and r.json()["accepted"] == 5
        msg = ws.receive_json()
        assert msg["type"] == "samples" and msg["feed"]["source"] == "pytest" and "lookahead" in msg
    feeds = c.get("/api/live").json()["feeds"]
    assert any(f["well_id"] == wid and f["source"] == "pytest" for f in feeds)
    lf.FEEDS.pop(wid, None)


@needs_db
@pytest.mark.parametrize("name,metric", [("volve_ddr", "event precision (real daily reports)"),
                                         ("extraction", "event precision"), ("episodes", "outcome precision"),
                                         ("hindsight", "forewarned share (secondary)")])
def test_verify_recount_matches_the_stored_figure(name, metric):
    from app.db.session import SessionLocal
    from app.eval.evidence import evidence
    with SessionLocal() as db:
        d = evidence(db, name, metric)
    if d["stored"] is None:
        pytest.skip("eval not run on this database")
    assert d["rows"] and d["recount"]["matches_stored"], (d["stored"], d["recount"])


@needs_db
def test_verify_says_so_when_a_figure_has_no_rows():
    from app.db.session import SessionLocal
    from app.eval.evidence import evidence
    with SessionLocal() as db:
        d = evidence(db, "hazard_loo", "Brier score (model)")
    assert d["recount"] is None and "no row-level breakdown" in d["how"]


# --- reliability scripts ---------------------------------------------------------------------------------------------

def test_ops_scripts_are_valid_bash():
    for f in ("kupakosh-backup.sh", "kupakosh-health.sh", "install_ops.sh", "restore_backup.sh"):
        assert subprocess.run(["bash", "-n", str(ROOT / "deploy" / f)]).returncode == 0, f
