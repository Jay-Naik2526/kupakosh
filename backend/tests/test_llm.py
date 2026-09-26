"""LLM layer without network: a fake transport stands in for Gemini/Groq."""
import json

from app.extract.llm_extract import _checker
from app.llm import client
from app.llm.schemas import ExtractedEvent, json_schema

TEXT = "While drilling at 2,450 m total losses of 120 bbl occurred with 10.2 ppg mud; pumped LCM pill, returns regained."
GOOD = {"hazard": "lost_circulation", "md_m": 2450, "quantity": 120, "quantity_unit": "bbl", "mud_weight_ppg": 10.2,
        "actions": ["lcm_pill"], "outcome_hint": "resolved", "evidence_span": "total losses of 120 bbl", "confidence": 0.9}


def fake(replies):
    it = iter(replies)
    calls = []
    def t(provider, prompt, schema):
        calls.append(prompt)
        return next(it)
    return t, calls


def test_valid_answer_accepted():
    t, calls = fake([json.dumps(GOOD)])
    obj, trace = client.structured("p", json_schema(), ExtractedEvent, transport=t, extra_check=_checker(TEXT, 4000))
    assert obj and obj.hazard == "lost_circulation" and len(calls) == 1


def test_non_verbatim_evidence_retried_once_then_rejected():
    bad = dict(GOOD, evidence_span="massive losses")  # not in the sentence
    t, calls = fake([json.dumps(bad), json.dumps(bad)])
    obj, trace = client.structured("p", json_schema(), ExtractedEvent, transport=t, extra_check=_checker(TEXT, 4000))
    assert obj is None and len(calls) == 2 and "previous answer was invalid" in calls[1]


def test_retry_fixes_invalid_json_and_bad_enum():
    t, calls = fake(["not json", json.dumps(GOOD)])
    obj, _ = client.structured("p", json_schema(), ExtractedEvent, transport=t, extra_check=_checker(TEXT, 4000))
    assert obj is not None
    t, _ = fake([json.dumps(dict(GOOD, hazard="volcano")), json.dumps(dict(GOOD, hazard="volcano"))])
    obj, _ = client.structured("p", json_schema(), ExtractedEvent, transport=t)
    assert obj is None


def test_depth_and_mud_weight_bounds():
    t, _ = fake([json.dumps(dict(GOOD, md_m=9000)), json.dumps(dict(GOOD, mud_weight_ppg=40))])
    obj, _ = client.structured("p", json_schema(), ExtractedEvent, transport=t, extra_check=_checker(TEXT, 4000))
    assert obj is None


def test_no_key_means_unavailable(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert not client.available()
