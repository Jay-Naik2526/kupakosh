"""Pydantic schema for LLM extraction (SPEC.md §9.1). Every LLM answer is validated against it."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.config import taxonomy


class ExtractedEvent(BaseModel):
    hazard: str                                   # a taxonomy hazard key, or "none"
    md_m: float | None = None
    quantity: float | None = None
    quantity_unit: Literal["bbl", "m3"] | None = None
    mud_weight_ppg: float | None = None
    actions: list[str] = Field(default_factory=list)
    outcome_hint: Literal["resolved", "partial", "unresolved", "worsened", "unknown"] = "unknown"
    evidence_span: str
    confidence: float = Field(ge=0, le=1)

    @field_validator("hazard")
    @classmethod
    def _hazard(cls, v: str) -> str:
        if v != "none" and v not in taxonomy()["hazards"]:
            raise ValueError(f"unknown hazard {v!r}")
        return v

    @field_validator("actions")
    @classmethod
    def _actions(cls, v: list[str]) -> list[str]:
        bad = [a for a in v if a not in taxonomy()["actions"] and a != "other"]
        if bad:
            raise ValueError(f"unknown actions {bad}")
        return v


def json_schema() -> dict:
    """Plain JSON schema sent to the model (enums filled from config/taxonomy.yaml)."""
    tax = taxonomy()
    return {
        "type": "object",
        "properties": {
            "hazard": {"type": "string", "enum": list(tax["hazards"]) + ["none"]},
            "md_m": {"type": "number", "nullable": True},
            "quantity": {"type": "number", "nullable": True},
            "quantity_unit": {"type": "string", "enum": ["bbl", "m3"], "nullable": True},
            "mud_weight_ppg": {"type": "number", "nullable": True},
            "actions": {"type": "array", "items": {"type": "string", "enum": list(tax["actions"]) + ["other"]}},
            "outcome_hint": {"type": "string", "enum": ["resolved", "partial", "unresolved", "worsened", "unknown"]},
            "evidence_span": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["hazard", "evidence_span", "confidence", "actions", "outcome_hint"],
    }
