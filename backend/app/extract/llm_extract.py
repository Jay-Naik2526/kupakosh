"""Pass 2 of extraction (SPEC.md §9.1): the LLM re-reads sentences the rules flagged.

Runs only when an API key is configured. For each rule event:
  * ask for ExtractedEvent JSON (schema from config/taxonomy.yaml)
  * validate: Pydantic types, evidence_span must be a verbatim substring, depth within [0, TD], MW within the ppg range
  * agreement with the rule hazard raises confidence (config llm.agree_bonus) and sets method="rule+llm";
    disagreement or an invalid answer marks the event needs_review (the rule result is kept, never overwritten)
"""
from __future__ import annotations

from sqlalchemy import select

from app.config import cfg
from app.db.models import Event, Passage, Well
from app.llm import client
from app.llm.schemas import ExtractedEvent, json_schema

PROMPT = """You extract drilling problems from one sentence of a drilling report.
Sentence: \"\"\"{text}\"\"\"
Return: hazard (one allowed key, or "none"), md_m (measured depth in metres if stated, convert feet x0.3048), quantity and
quantity_unit if a lost/gained volume is stated, mud_weight_ppg if stated (sg x8.345), actions taken, outcome_hint, and
evidence_span = the exact words from the sentence that show the hazard (copy them verbatim), confidence 0..1.
Use only what the sentence says. If it is not a drilling problem, hazard = "none"."""


def _checker(text: str, td: float | None):
    lo, hi = cfg()["extract"]["mw_range_ppg"]

    def check(o: ExtractedEvent) -> str | None:
        if o.evidence_span not in text:
            return "evidence_span is not a verbatim substring of the sentence"
        if o.md_m is not None and (o.md_m < 0 or (td is not None and o.md_m > td)):
            return f"md_m {o.md_m} outside [0, {td}]"
        if o.mud_weight_ppg is not None and not lo <= o.mud_weight_ppg <= hi:
            return f"mud_weight_ppg {o.mud_weight_ppg} outside [{lo}, {hi}]"
        return None
    return check


def run(db, log=print, transport=None, doc_ids: set[int] | None = None) -> dict:
    if transport is None and not client.available():
        log("llm pass: skipped (no GEMINI_API_KEY / GROQ_API_KEY) — events stay method='rule'")
        return {"skipped": True}
    c, ce = cfg()["llm"], cfg()["extract"]
    q = select(Event, Passage, Well).join(Passage, Passage.id == Event.passage_id).join(Well, Well.id == Event.well_id)
    if doc_ids is not None:
        q = q.where(Passage.document_id.in_(doc_ids))
    n = {"calls": 0, "agree": 0, "disagree": 0, "invalid": 0}
    for ev, p, w in db.execute(q.order_by(Event.id).limit(c["max_calls"])):
        obj, trace = client.structured(PROMPT.format(text=p.text), json_schema(), ExtractedEvent, transport=transport,
                                       extra_check=_checker(p.text, w.td_md_m))
        n["calls"] += 1
        if obj is None:
            ev.needs_review = True
            n["invalid"] += 1
        elif obj.hazard == ev.hazard:
            ev.method = "rule+llm"
            ev.confidence = round(min(1.0, max(ev.confidence, obj.confidence) + c["agree_bonus"]), 3)
            ev.needs_review = ev.confidence < ce["review_threshold"]
            n["agree"] += 1
        else:
            ev.needs_review = True  # rules and LLM disagree -> a human decides
            n["disagree"] += 1
    db.flush()
    log(f"llm pass: {n}")
    return n
