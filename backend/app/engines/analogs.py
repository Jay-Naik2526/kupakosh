"""V2 USP: Global Analog Memory for Indian basins (docs/PLAN_V2.md).

India has almost no public well-level data in this database: "Indian wells" here are names
listed in NDR/DGH basin-summary tables (app.ingest.india), with no coordinates, no formation
tops and no daily reports (see `app.db.models.Basin`). To still say something useful for an
Indian basin, formation or lithology + depth band, this module looks worldwide — across the
other 8 countries' formation tops (Sodir/Norway, NLOG/Netherlands, NSTA/UK, FORGE/USA,
FORCE-2020-labelled logs/Australia) — for ANALOG INTERVALS: rock of the same broad lithology
class, at an overlapping depth, and reports what actually happened there (recorded hazards,
what fixed them). Every number traces to a real `FormationTop`/`Event`/`Episode` row.

Honesty rule (SPEC.md §0.4, §0.7): this is analogue evidence from *other countries'* public
wells, never a claim about Indian rock. Every response carries `caveat` verbatim from
config/analogs.yaml. Lithology classification rules are documented in that file, not here.

Two moving parts:
  * `_index()` — a process-wide, lru_cache'd list of classified (well, interval) rows built once
    from `formation_top`. Cleared by `reset()`. The lead should add `analogs.reset()` to
    `app/engines/caches.py::reset_all()` (see v2_common.md — I do not edit that shared file).
  * `find_analogs(...)` — the query: classify, overlap-filter, group by well, Bayesian posterior
    per hazard (same Beta shape as `app.engines.hazard`), top fixes from `app.engines.ledger`.
`basin_suggestions(...)` answers "what should I even search for?" for an Indian basin, by
scanning that basin's own NDR passages for lithology/formation-name keywords and depth numbers —
never inventing a name that is not literally present in a passage.
"""
from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import yaml
from scipy.stats import beta as beta_dist
from sqlalchemy import select

from app.config import CONFIG_DIR, cfg, lithology, taxonomy
from app.db.models import Basin, FormationTop, Passage
from app.db.session import SessionLocal
from app.engines import hazard as hz
from app.engines.context import ctx
from app.engines.ledger import ledger as ledger_fn


@lru_cache
def acfg() -> dict:
    p = CONFIG_DIR / "analogs.yaml"
    return yaml.safe_load(p.read_text())


def canonical_class(name: str) -> str | None:
    """User-typed class name -> one of acfg()['classes'], or None if unrecognised."""
    if not name:
        return None
    n = name.strip().lower()
    a = acfg()
    if n in a["classes"]:
        return n
    return a["class_aliases"].get(n)


_WORD_RE_CACHE: dict[str, re.Pattern] = {}


def _word(kw: str) -> re.Pattern:
    pat = _WORD_RE_CACHE.get(kw)
    if pat is None:
        pat = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
        _WORD_RE_CACHE[kw] = pat
    return pat


def classify_lithology(formation: str | None, lithology_field: str | None, source: str | None) -> str | None:
    """Map one FormationTop row to a class in acfg()['classes'], or None (unclassified — never guessed).
    Rules are documented in config/analogs.yaml (sodir uses the curated lithology.yaml unit map;
    every other source is matched by whole-word keyword against its own lithology text, else its
    formation name; more than one class's keywords in the same text -> 'mixed')."""
    a = acfg()
    if source == "sodir":
        code = lithology().get((formation or "").strip())
        if code:
            mapped = a["sodir_code_to_class"].get(code)
            if mapped:
                return mapped
    text = f"{lithology_field or ''} {formation or ''}"
    if not text.strip():
        return None
    matched = {cls for cls, kws in a["keywords"].items() if any(_word(kw).search(text) for kw in kws)}
    if not matched:
        return None
    if len(matched) > 1:
        return "mixed"
    return next(iter(matched))


def overlap_m(a_top: float, a_base: float, b_top: float, b_base: float) -> float:
    """Metres shared between [a_top, a_base] and [b_top, b_base] (0 if they don't overlap)."""
    return max(0.0, min(a_base, b_base) - max(a_top, b_top))


@lru_cache(maxsize=1)
def _index() -> dict[str, list[dict]]:
    """All classified FormationTop rows with both top_md_m and base_md_m, grouped by class.
    Built once per process; call `reset()` after a rebuild (see module docstring)."""
    by_class: dict[str, list[dict]] = defaultdict(list)
    with SessionLocal() as db:
        rows = db.execute(select(FormationTop.well_id, FormationTop.formation, FormationTop.lithology,
                                  FormationTop.top_md_m, FormationTop.base_md_m, FormationTop.source,
                                  FormationTop.source_ref).where(FormationTop.top_md_m.is_not(None),
                                                                  FormationTop.base_md_m.is_not(None))).all()
    for well_id, formation, lith, top, base, source, source_ref in rows:
        if base <= top:
            continue
        cls = classify_lithology(formation, lith, source)
        if cls is None:
            continue
        by_class[cls].append({"well_id": well_id, "formation": formation, "source": source,
                              "top_md_m": top, "base_md_m": base, "source_ref": source_ref})
    return dict(by_class)


def reset():
    _index.cache_clear()


def _matches(lithology_class: str, top_m: float, base_m: float) -> list[dict]:
    a = acfg()
    out = []
    for row in _index().get(lithology_class, []):
        ov = overlap_m(row["top_md_m"], row["base_md_m"], top_m, base_m)
        if ov >= a["min_overlap_m"]:
            r = dict(row)
            r["overlap_m"] = ov
            r["overlap_frac"] = min(1.0, ov / (base_m - top_m))
            out.append(r)
    return out


def _posterior(hazard_key: str, well_weight: dict[int, float], well_hit: dict[int, bool], source: str | None) -> dict:
    """Same Beta-posterior shape as app.engines.hazard.posterior, but the evidence is analog
    (lithology+depth) wells rather than geographic offsets, so it is computed here rather than by
    calling that function directly. The prior still reuses hz.base_rate (a sentinel formation name
    that is never in any well's penetrated set forces its 'all_formations' branch: the hazard's
    global recorded rate, optionally within one data source)."""
    a = acfg()
    base, base_n, base_scope = hz.base_rate("__analog_global__", hazard_key, source)
    a0, b0 = a["prior_strength"] * base, a["prior_strength"] * (1 - base)
    sw = sw2 = swy = 0.0
    for wid, w in well_weight.items():
        if w <= 0:
            continue
        y = 1 if well_hit.get(wid) else 0
        sw += w
        sw2 += w * w
        swy += w * y
    alpha, beta_ = a0 + swy, b0 + (sw - swy)
    n_eff = (sw * sw / sw2) if sw2 > 0 else 0.0
    lo_q = (1 - a["ci"]) / 2
    mean = alpha / (alpha + beta_)
    lo, hi = beta_dist.ppf([lo_q, 1 - lo_q], alpha, beta_)
    status = "ok" if round(n_eff, 1) >= a["min_neff"] else "insufficient evidence"
    n_with_event = sum(1 for hit in well_hit.values() if hit)
    return {"hazard": hazard_key, "label": taxonomy()["hazards"][hazard_key]["label"], "status": status,
            "mean": round(float(mean), 4), "ci": [round(float(lo), 4), round(float(hi), 4)], "ci_level": a["ci"],
            "n_eff": round(n_eff, 2), "n_wells": len(well_weight), "n_with_event": n_with_event,
            "prior": {"base_rate": round(base, 4), "base_n": base_n, "scope": base_scope, "strength": a["prior_strength"], "source": source}}


def find_analogs(lithology_class: str, top_m: float, base_m: float, hazards: list[str] | None = None,
                  basin: str | None = None, db=None) -> dict:
    a = acfg()
    cls = canonical_class(lithology_class)
    query = {"lithology": lithology_class, "canonical_class": cls, "top_m": top_m, "base_m": base_m,
             "hazards": hazards, "basin": basin}
    if cls is None:
        return {"query": query, "error": f"unrecognised lithology class '{lithology_class}'", "classes": a["classes"],
                "n_intervals": 0, "n_wells": 0, "by_country": [], "hazards": [], "fixes": [], "caveat": a["caveat"]}
    if base_m <= top_m:
        return {"query": query, "error": "base must be greater than top", "n_intervals": 0, "n_wells": 0,
                "by_country": [], "hazards": [], "fixes": [], "caveat": a["caveat"]}
    basin_obj = None
    if basin:
        with SessionLocal() as bdb:
            basin_obj = bdb.execute(select(Basin).where(Basin.slug == basin)).scalar_one_or_none()
        query["basin_name"] = basin_obj.name if basin_obj else None
        query["basin_found"] = basin_obj is not None

    cx = ctx()
    matches = _matches(cls, top_m, base_m)
    by_well: dict[int, list[dict]] = defaultdict(list)
    for m in matches:
        by_well[m["well_id"]].append(m)

    country_intervals: dict[str, int] = defaultdict(int)
    country_wells: dict[str, set[int]] = defaultdict(set)
    country_documented: dict[str, set[int]] = defaultdict(set)
    well_weight: dict[int, float] = {}
    well_hit: dict[str, dict[int, bool]] = defaultdict(dict)  # hazard -> well_id -> bool
    sources_seen: list[str] = []
    for wid, rows in by_well.items():
        w = cx.wells.get(wid)
        country = w.country if w else None
        country_intervals[country or "unknown"] += len(rows)
        country_wells[country or "unknown"].add(wid)
        well_weight[wid] = max(r["overlap_frac"] for r in rows)
        if wid not in cx.documented:
            continue
        country_documented[country or "unknown"].add(wid)
        sources_seen.append(w.source if w else None)
        band_lo = min(r["top_md_m"] for r in rows)  # widest matched span for this well, clipped to the query band
        band_hi = max(r["base_md_m"] for r in rows)
        lo, hi = max(band_lo, top_m), min(band_hi, base_m)
        events = [e for e in cx.events.get(wid, []) if e.md_m is not None and lo <= e.md_m <= hi]
        for hkey in (hazards or list(taxonomy()["hazards"].keys())):
            well_hit[hkey][wid] = any(e.hazard == hkey for e in events)

    documented_wells = {wid for s in country_documented.values() for wid in s}
    dom_source = max(set(sources_seen), key=sources_seen.count) if sources_seen else None

    by_country = [{"country": c or "unknown", "n_intervals": country_intervals[c], "n_wells": len(country_wells[c]),
                  "n_wells_documented": len(country_documented.get(c, set()))}
                 for c in sorted(country_wells, key=lambda k: -len(country_wells[k]))]

    hazard_keys = [h for h in (hazards or list(taxonomy()["hazards"].keys())) if h in taxonomy()["hazards"]]
    hazard_rows = []
    for hkey in hazard_keys:
        weights_for_hazard = {wid: well_weight[wid] for wid in documented_wells}
        post = _posterior(hkey, weights_for_hazard, well_hit.get(hkey, {}), dom_source)
        examples = []
        for wid, hit in sorted(well_hit.get(hkey, {}).items(), key=lambda kv: (not kv[1], -well_weight[kv[0]])):
            if not hit:
                continue
            for e in cx.events.get(wid, []):
                if e.hazard == hkey and e.source_ref:
                    examples.append(e.source_ref)
            if len(examples) >= a["max_examples"]:
                break
        if not examples:  # fall back to the matched intervals themselves so a query is never silent about *where*
            examples = [r["source_ref"] for wid in list(documented_wells)[: a["max_examples"]] for r in by_well[wid][:1]]
        post["examples"] = examples[: a["max_examples"]]
        hazard_rows.append(post)

    fixes: list[dict] = []
    if documented_wells:
        with SessionLocal() as ldb:
            single_hazard = hazard_keys[0] if len(hazard_keys) == 1 else None
            L = ledger_fn(ldb, hazard=single_hazard, formation=None, well_ids=sorted(documented_wells))
        fixes = L["rows"][: a["max_examples"]]

    caveat = a["caveat"]
    if basin_obj is not None:
        caveat = f"{caveat} Looked up against the {basin_obj.name} basin summary (NDR/DGH) — informational label only, no well-level Indian data was matched."
    elif basin:
        caveat = f"{caveat} Basin slug '{basin}' was not found among the loaded NDR basins; ignored."

    return {"query": query, "n_intervals": len(matches), "n_wells": len(by_well), "by_country": by_country,
            "hazards": hazard_rows, "fixes": fixes, "caveat": caveat}


# --- Indian basin suggestions --------------------------------------------------------------

def _depth_hints(text: str) -> list[str]:
    pat = re.compile(acfg()["depth_hint_pattern"], re.I)
    return [m.group(1) for m in pat.finditer(text)]


def basin_suggestions() -> list[dict]:
    """List Indian basins with lithology/formation/depth suggestions grounded in that basin's own
    NDR passages. Never invents a name: a suggestion only appears if the exact word/number is
    present in a real passage, which is quoted with its source_ref."""
    a = acfg()
    out = []
    with SessionLocal() as db:
        basins = db.execute(select(Basin)).scalars().all()
        for b in basins:
            suggestions: list[dict] = []
            if b.document_id is None:
                out.append({"slug": b.slug, "name": b.name, "url": b.url, "category": b.category, "suggestions": []})
                continue
            passages = db.execute(select(Passage.locator, Passage.text).where(Passage.document_id == b.document_id)).all()
            seen_classes: set[str] = set()
            seen_names: set[str] = set()
            for locator, text in passages:
                if not text:
                    continue
                ref = f"doc:{b.document_id}#{locator}"
                if len(seen_classes) < len(a["classes"]):
                    for cls, kws in a["keywords"].items():
                        if cls in seen_classes:
                            continue
                        if any(_word(kw).search(text) for kw in kws):
                            depths = _depth_hints(text)
                            suggestions.append({"type": "lithology", "value": cls, "text": text[:280], "source_ref": ref,
                                                "depth_hints_m": depths[:3]})
                            seen_classes.add(cls)
                for name in a["formation_name_hints"]:
                    if name in seen_names:
                        continue
                    if re.search(r"\b" + re.escape(name) + r"\b", text, re.I):
                        depths = _depth_hints(text)
                        suggestions.append({"type": "formation", "value": name, "text": text[:280], "source_ref": ref,
                                            "depth_hints_m": depths[:3]})
                        seen_names.add(name)
                if len(suggestions) >= 25:
                    break
            out.append({"slug": b.slug, "name": b.name, "url": b.url, "category": b.category, "suggestions": suggestions})
    return out
