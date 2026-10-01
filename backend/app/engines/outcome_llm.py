"""Episode outcome read by a local language model (offline, Ollama), with a verbatim-evidence check.

The rule linker (engines.episodes) reads outcomes from fixed phrases and measured 0.55 accuracy on a fresh blind
sample. This module gives the same window of report text (the problem sentence and the lines that follow it) to a
local model and asks for one of the SPEC.md §8 outcomes plus the exact words that show it.

Guards (SPEC.md §9.1 style):
  * output is JSON validated by Pydantic; one retry, then the rule result is kept;
  * the quoted evidence must appear verbatim in the window text, otherwise the answer is rejected;
  * "unknown" needs no quote; any other outcome without a verifiable quote falls back to the rule result.
Nothing leaves the machine: the model runs locally.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

OUTCOMES = ("resolved", "partial", "unresolved", "worsened", "unknown")


class OutcomeAnswer(BaseModel):
    outcome: Literal["resolved", "partial", "unresolved", "worsened", "unknown"]
    evidence: str = Field("", max_length=400)


SCHEMA = {
    "type": "object",
    "properties": {"outcome": {"type": "string", "enum": list(OUTCOMES)}, "evidence": {"type": "string"}},
    "required": ["outcome", "evidence"],
}

PROMPT = """You read drilling reports. A drilling problem was recorded in the FIRST line below. The lines after it are what
the report says next. Decide what happened to THIS problem, using only the text.

Problem type: {hazard}

Outcomes:
- resolved: the problem was fixed or overcome (pipe freed or came free, tight spot passed or cleared, losses cured or
  stopped, full returns regained, well static or killed, fish/junk recovered, torque back to normal, drilling or
  tripping continued normally past it).
- partial: only partly fixed (losses reduced but continuing, most of the fish recovered, "not entirely successful").
- unresolved: not fixed (still stuck/losing, fish left in hole, string cut or backed off, hole plugged back or
  sidetracked, abandoned, attempts failed).
- worsened: it got worse or caused a bigger problem (losses became total, kick or blowout followed, well control
  incident, fire, stuck deeper).
- unknown: the text does not say what happened to this problem.

Rules: judge only this problem, not other problems mentioned later. If an outcome other than "unknown" is chosen,
"evidence" must be an exact quote (copied word for word, at most 25 words) from the text that shows it. If the text
does not say, answer "unknown" with empty evidence.

Text:
{text}

Answer as JSON: {{"outcome": ..., "evidence": ...}}"""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def read_outcome(hazard_label: str, lines: list[str], transport=None) -> tuple[str | None, str | None, dict]:
    """Returns (outcome, evidence quote, trace). (None, None, trace) when the model gave no valid, verifiable answer."""
    from app.llm.client import structured
    text = "\n".join(f"[{i + 1}] {l.strip()}" for i, l in enumerate(lines) if l and l.strip())
    window = _norm(" ".join(lines))

    def check(a: OutcomeAnswer) -> str | None:
        if a.outcome == "unknown":
            return None
        q = _norm(a.evidence).strip(" .\"'")
        if len(q) < 4 or q not in window:
            return "evidence must be an exact quote from the text"
        return None

    obj, trace = structured(PROMPT.format(hazard=hazard_label, text=text[:6000]), SCHEMA, OutcomeAnswer,
                            transport=transport, extra_check=check, only=["ollama"])
    if obj is None:
        return None, None, trace
    return obj.outcome, (obj.evidence or None), trace
