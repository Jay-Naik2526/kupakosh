"""Pass 1 extraction: regex + keyword taxonomy (SPEC.md §9.1).

Works sentence-by-sentence on real report text. Every hit keeps the verbatim
sentence as evidence_span, so any fact can be traced back to its source line.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import cfg, taxonomy
from app.ingest.units import ft_to_m, sg_to_ppg


@dataclass
class Hit:
    hazard: str
    span: tuple[int, int]
    md_m: float | None = None
    depth_raw: str | None = None
    quantity: float | None = None
    quantity_unit: str | None = None
    mud_weight_ppg: float | None = None
    severity: str = "medium"
    confidence: float = 0.0
    actions: list[tuple[str, str]] = field(default_factory=list)


@lru_cache
def _compiled():
    tax = taxonomy()
    hz = {}
    for k, v in tax["hazards"].items():
        hz[k] = (
            [re.compile(p, re.I) for p in v.get("include", [])],
            [re.compile(p, re.I) for p in v.get("exclude", []) or []],
        )
    acts = {k: [re.compile(p, re.I) for p in v] for k, v in tax["actions"].items()}
    outs = {k: [re.compile(p, re.I) for p in v] for k, v in tax["outcomes"].items()}
    return hz, acts, outs


# depths: "at 1544 m", "3456 m MD", "4131 m (13554')", "9,850 ft", "7542'"
_DEPTH_M = re.compile(r"(?<![\d.])(\d{1,2}[ ,]?\d{3}|\d{2,4})(?:[.,]\d+)?\s?m(?:\s?(?:MD|TVD|RKB|MSL|BRT))?\b(?![\s]?(?:3|³|/))", re.I)
_DEPTH_FT = re.compile(r"(?<![\d.])(\d{1,2}[ ,]?\d{3}|\d{2,5})(?:\.\d+)?\s?(?:ft|feet|')(?![\w])", re.I)
_QTY = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s?(bbls?|barrels|m3|m³)\b", re.I)
_MW = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,3})\s?(ppg|sg|s\.g\.|g/cc|g/cm3|g/cm³|lb/gal)\b", re.I)
_SEV_HIGH = re.compile(r"\btotal\b|\bsevere\b|\bmajor\b|\bblowout\b|\babandon|\bjunk well\b|\bsignificant\b|\bregional records?\b", re.I)
_SEV_LOW = re.compile(r"\bminor\b|\bslight\b|\bsmall\b|\bseepage\b|\bsome\b|\bminimal\b", re.I)
_NEG = re.compile(r"\b(no|without|not|never|nor|avoid(ed)?|free of|absence of|potential|possible|prognosed|risk of|to check for)\b", re.I)
_NPT_H = re.compile(r"(\d+(?:\.\d+)?)\s?(hrs?|hours)\b", re.I)
_NPT_D = re.compile(r"(\d+(?:\.\d+)?)\s?days?\b", re.I)


def _num(s: str) -> float:
    return float(re.sub(r"[ ,]", "", s))


_RELATIVE_AFTER = re.compile(r"^\s*(\([^)]*\)\s*)?(beyond|above|below|deeper|shallower|thick|of|higher|lower|shallow|deep|long|into|interval|net|gross|apart|away|further|more|less|hole section|fish|joints?|stands?|piece|pipe|of pipe|drill pipe|section)\b", re.I)
_FT_RATE_AFTER = re.compile(r"^\s*(-\s*[\d,]+\s?['’]?\s*)?(FPH|fph|ft/hr|feet per hour|/hr|per hour|total|high|low|right|left|of new hole|of hole|in \d|lbs?\b|-lbs?\b|klbs)", re.I)
_RELATIVE_BEFORE = re.compile(r"\b(only|ca\.?|about|approximately|some|another|additional|extra|a further)\s*$", re.I)


def depths(text: str) -> list[tuple[int, float, str]]:
    """All absolute depth mentions in metres: (char_pos, md_m, raw).
    Relative distances ('22 m beyond', '10 m of sandstone', '19 m deep compared to prognosis') are skipped."""
    out = []
    for m in _DEPTH_M.finditer(text):
        v = _num(m.group(1))
        if _RELATIVE_AFTER.match(text[m.end():m.end() + 30]) or _RELATIVE_BEFORE.search(text[max(0, m.start() - 20):m.start()]):
            continue
        if 5 <= v <= 12000:
            out.append((m.start(), v, m.group(0)))
    metre_pos = {p for p, _, _ in out}
    for m in _DEPTH_FT.finditer(text):
        v = _num(m.group(1))
        after = text[m.end():m.end() + 30]
        if _RELATIVE_AFTER.match(after) or _FT_RATE_AFTER.match(after) or _RELATIVE_BEFORE.search(text[max(0, m.start() - 20):m.start()]):
            continue
        if text[max(0, m.start() - 1):m.start()] == "(":
            continue  # "(147') Total" footage drilled
        # skip the feet echo inside "4131 m (13554')" — metres already captured nearby
        if any(abs(m.start() - p) < 18 for p in metre_pos):
            continue
        if cfg()["extract"]["min_depth_ft"] <= v <= 40000:
            out.append((m.start(), round(ft_to_m(v), 1), m.group(0)))
    return sorted(out)


def nearest_depth(text: str, pos: int) -> tuple[float | None, str | None]:
    ds = depths(text)
    if not ds:
        return None, None
    # prefer the first depth after the keyword ("losses started at 220 m"), else nearest before
    after = [d for d in ds if d[0] >= pos]
    best = after[0] if after and after[0][0] - pos < 120 else min(ds, key=lambda d: abs(d[0] - pos))
    return best[1], best[2]


def _negated(text: str, start: int) -> bool:
    """Negation only counts inside the same clause ('No shallow gas was seen, but tight spots...' is not negated)."""
    window = text[max(0, start - 45):start]
    window = re.split(r"[,;:]|\bbut\b|\bhowever\b|\balthough\b", window)[-1]
    return bool(_NEG.search(window))


def extract_sentence(text: str, td_md_m: float | None = None) -> list[Hit]:
    hz, acts, _ = _compiled()
    c = cfg()["extract"]
    mw_lo, mw_hi = c["mw_range_ppg"]
    hits: list[Hit] = []
    for hazard, (inc, exc) in hz.items():
        m = next((mm for p in inc for mm in [p.search(text)] if mm), None)
        if not m:
            continue
        if any(p.search(text) for p in exc):
            continue
        conf = c["conf_rule_base"]
        if _negated(text, m.start()):
            continue  # "No tight spots", "without losses": a statement that the hazard did NOT happen
        h = Hit(hazard=hazard, span=m.span())
        h.md_m, h.depth_raw = nearest_depth(text, m.start())
        if h.md_m is not None and td_md_m and h.md_m > td_md_m + 1:
            h.md_m, h.depth_raw = None, None  # validation: depth must lie within [0, TD]
        if h.md_m is not None:
            conf += c["conf_depth_bonus"]
        q = _QTY.search(text)
        if q:
            h.quantity = float(q.group(1))
            h.quantity_unit = "m3" if q.group(2).lower().startswith("m") else "bbl"
        mw = _MW.search(text)
        if mw:
            v = float(mw.group(1))
            unit = mw.group(2).lower()
            ppg = v if unit in ("ppg", "lb/gal") else sg_to_ppg(v)
            if mw_lo <= ppg <= mw_hi:
                h.mud_weight_ppg = round(ppg, 2)
        h.severity = "high" if _SEV_HIGH.search(text) else "low" if _SEV_LOW.search(text) else "medium"
        h.actions = find_actions(text)
        h.confidence = round(min(conf, 1.0), 3)
        hits.append(h)
    return hits


def find_actions(text: str) -> list[tuple[str, str]]:
    _, acts, _ = _compiled()
    out = []
    for a, pats in acts.items():
        for p in pats:
            m = p.search(text)
            if m:
                out.append((a, m.group(0)))
                break
    return out


def find_outcome(text: str) -> tuple[str, str] | None:
    """Return (outcome, matched phrase). Order: worsened > unresolved > partial > resolved."""
    _, _, outs = _compiled()
    for k in ("worsened", "unresolved", "partial", "resolved"):
        for p in outs[k]:
            m = p.search(text)
            if m:
                return k, m.group(0)
    return None


def stated_npt_hours(text: str) -> float | None:
    """Lost time explicitly stated in text, e.g. '10 hrs were lost', 'prolonged the rig time with 23 days'."""
    if not re.search(r"\blost\b|\bprolong|\bspent\b|\bextra\b|\bdelay|\bNPT\b|\bdowntime\b", text, re.I):
        return None
    m = _NPT_H.search(text)
    if m:
        return float(m.group(1))
    m = _NPT_D.search(text)
    if m:
        return float(m.group(1)) * 24
    return None
