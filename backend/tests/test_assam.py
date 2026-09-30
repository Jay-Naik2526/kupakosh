"""Upper Assam column: every fact is quoted from a real loaded sentence, nothing is invented."""
import re

from sqlalchemy import select

from app.db.models import Passage
from app.db.session import SessionLocal
from app.engines.assam import column, scfg


def _passage(ref: str) -> str:
    doc, loc = ref[len("doc:"):].split("#", 1)
    with SessionLocal() as db:
        return db.scalar(select(Passage.text).where(Passage.document_id == int(doc), Passage.locator == loc))


def test_every_fact_is_a_verbatim_quote_of_a_real_sentence():
    col = column()
    assert col["caveat"] == scfg()["caveat"]
    assert len(col["formations"]) == len(scfg()["formations"])
    for f in col["formations"]:
        name = re.compile(r"\b(" + "|".join(re.escape(n) for n in f["names"]) + r")\b", re.I)
        facts = [f["lithology"], f["age"], *f["roles"], *f["depth_mentions"], *f["quotes"]]
        for fact in [x for x in facts if x]:
            text = _passage(fact["source_ref"])
            assert text == fact["text"], fact["source_ref"]
            assert name.search(text), (f["key"], fact["source_ref"])  # the sentence really names this formation
        if f["age"]:
            assert f["age"]["value"].lower() in f["age"]["text"].lower()
        for d in f["depth_mentions"]:
            assert str(d["depth_m"]) in d["text"]


def test_no_rock_type_means_no_analog_numbers():
    for f in column()["formations"]:
        if f["lithology"] is None:
            assert f["analogs"] is None
        elif f["analogs"] is not None:
            assert f["analogs"]["lithology"] == f["lithology"]["class"]
            for h in f["analogs"]["hazards"]:
                assert 0 <= h["ci"][0] <= h["mean"] <= h["ci"][1] <= 1
                assert h["n_with_event"] > 0


def test_known_units_read_from_the_records():
    by = {f["key"]: f for f in column()["formations"]}
    assert by["tipam"]["lithology"]["class"] == "sandstone"
    assert by["girujan"]["lithology"]["class"] == "claystone"
    assert by["sylhet"]["lithology"]["class"] == "limestone"
    assert by["tipam"]["age"]["value"].endswith("Miocene")
