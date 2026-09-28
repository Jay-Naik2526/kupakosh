"""V1 USP: the Hindsight Test — blind replay proof (docs/PLAN_V2.md USP1).

For every documented well W we pretend we are drilling it blind: every alert is computed from
OTHER wells only (W itself and its parent/sidetracks are removed from the offset list, exactly
like the leave-one-well-out check in app.eval.run.hazard_loo). Walking W's own formation column
gives one "cell" per (well, formation, hazard) — the unit the honest metric is built on.

Two alert rules (config hindsight.alert_mode):
  * "elevated" (default) — flag a cell when the blind posterior's lower 80% credible bound is
    ABOVE the field base rate for that (formation, hazard, source) AND mean/base >= hindsight.rr_min
    (default 2.0). An absolute probability threshold is the wrong test for a rare hazard: 8% can be
    a very large elevation over a 1% base rate, while 8% is still "alert" under an absolute cut.
  * "absolute" (secondary, kept for comparison) — the original rule: posterior mean >=
    hazard.alert_threshold with enough evidence.

Primary honest metric: LIFT. Across every walked cell, split into "flagged" vs "not flagged" by
the chosen rule and compare the recorded-event rate in each group (Wilson 95% interval on each
rate; the lift's own interval is an approximate ratio-of-bounds, stated as such). This is compared
against a fair baseline that flags the same NUMBER of cells, chosen by base rate alone (top-k) —
so lift is skill over "just knowing the field average", not skill over guessing nothing.
Forewarned share and median lead distance are reported as secondary, per-event metrics.

Honesty notes (SPEC.md §0.4/§0.7):
  * A flagged cell with no matching real event is "no recorded event", never "false alarm" —
    reports under-record problems, so absence of a record is not evidence of no problem.
  * If lift is close to 1 or its interval spans 1, the summary says "no measured lift yet" —
    never a headline number dressed up as a finding.
  * All numbers trace to a well id, a formation, and (for events) a `source_ref`.
"""
from __future__ import annotations

import json
import math
import threading
import time
from collections import defaultdict
from statistics import median

from app.config import DATA_DIR, cfg, taxonomy
from app.engines import hazard as hz
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.lookahead import formation_intervals
from app.engines.offsets import offsets_for_well

CACHE_PATH = DATA_DIR / "processed" / "hindsight_summary.json"
ENGINE_VERSION = 4  # bump when the cell walk or metrics change, so cached summaries are recomputed


def _hindsight_cfg() -> dict:
    c = cfg().get("hindsight") or {}
    return {
        "max_wells": c.get("max_wells"),          # None = no cap: every documented testable well
        "min_offsets": c.get("min_offsets", 3),
        "alert_mode": c.get("alert_mode", "elevated"),
        "rr_min": c.get("rr_min", 2.0),
        "watchlist_k": list(c.get("watchlist_k", [3, 5, 10])),
        "operating_thresholds": list(c.get("operating_thresholds", [0.4, 0.1, 0.05, 0.02])),
        "learned": c.get("learned") or {},
    }


LEARNED_MODES = ("learned_live", "learned_blind")


def _other_mode(mode: str) -> str:
    return "absolute" if mode in LEARNED_MODES or mode == "elevated" else "elevated"


_FAMILY: dict | None = None


def _family(well_id: int) -> frozenset[int]:
    """The well plus every well sharing its parent_well (sidetracks / re-entries): all hidden in a blind replay."""
    global _FAMILY
    cx = ctx()
    if _FAMILY is None or _FAMILY.get("_ctx") is not cx:
        fam: dict = defaultdict(set)
        for w in cx.wells.values():
            if w.parent_well:
                fam[w.parent_well].add(w.id)
        _FAMILY = {"_ctx": cx, "by_parent": {k: frozenset(v) for k, v in fam.items()}}
    parent = cx.wells[well_id].parent_well
    return (_FAMILY["by_parent"].get(parent, frozenset()) | {well_id}) if parent else frozenset({well_id})


def _blind_offsets(well_id: int) -> list[dict]:
    """Offsets for well_id with the well itself and any well sharing its parent_well (sidetracks /
    re-entries of the same wellbore) removed — the same non-independence rule as hazard_loo."""
    cx = ctx()
    parent = cx.wells[well_id].parent_well
    return [o for o in offsets_for_well(well_id) if cx.wells[o["well_id"]].parent_well != parent]


def _formation_top_md(ints: list[dict]) -> dict[str, float]:
    """First (shallowest) top_md_m per formation name, in case a name repeats down the column."""
    out: dict[str, float] = {}
    for i in ints:
        out.setdefault(i["formation"], i["top_md_m"])
    return out


def _cells_for_well(well_id: int, light: bool = False):
    """Walk well_id's whole formation column x every taxonomy hazard, blind to the well itself.
    `light=True` drops the per-cell evidence list (used for the big cross-well lift aggregation,
    where only mean/base/flags/y are needed); the single-well API keeps it (for the "why" detail).
    Returns (well, offs, ints, cells)."""
    cx = ctx()
    w = cx.wells[well_id]
    offs = _blind_offsets(well_id)
    ints = formation_intervals(well_id)
    forms = []
    for i in ints:
        if i["formation"] not in forms:
            forms.append(i["formation"])
    tops_md = _formation_top_md(ints)
    c = cfg()
    hc = _hindsight_cfg()
    la = c["lookahead"]["lookahead_m"]
    thr = c["hazard"]["alert_threshold"]
    rr_min = hc["rr_min"]
    info: dict[str, tuple[float, str, int]] = {}
    for k, i in enumerate(ints):
        if i["formation"] in info:
            continue
        nxt = ints[k + 1]["top_md_m"] if k + 1 < len(ints) else (w.td_md_m or i["top_md_m"])
        bottom = i.get("base_md_m") or nxt or i["top_md_m"]
        info[i["formation"]] = (max(0.0, bottom - i["top_md_m"]), i.get("lithology") or "unknown", k)
    n_offs_doc = sum(1 for o in offs if o["well_id"] in cx.documented)
    hidden = _family(well_id)  # the tested well and its sidetracks never feed its own prior / base rate
    cells = []
    for f in forms:
        top_md = tops_md[f]
        thick, lith, order = info.get(f, (0.0, "unknown", 0))
        alert_md = round(max(0.0, top_md - la), 1)
        for h in taxonomy()["hazards"]:
            # source=w.source: "the field base rate of the same source" (SPEC.md §9.5 prior_by_source)
            p = hz.posterior(f, h, offs, source=w.source, exclude=hidden)
            base = p["prior"]["base_rate"]  # Laplace-smoothed, so always > 0 (see hazard.base_rate)
            rr = p["mean"] / base if base > 0 else None
            flagged_elevated = p["status"] == "ok" and p["ci"][0] > base and rr is not None and rr >= rr_min
            flagged_absolute = p["status"] == "ok" and p["mean"] >= thr
            y = 1 if (well_id, f, h) in cx.ev_wf else 0
            cell = {
                "well_id": well_id, "source": w.source, "country": w.country,
                "formation": f, "formation_label": pretty(f), "hazard": h, "label": p["label"],
                "top_md_m": top_md, "alert_md_m": alert_md,
                "mean": p["mean"], "ci": p["ci"], "ci_level": p["ci_level"], "n_eff": p["n_eff"],
                "n_wells": p["n_wells"], "n_with_event": p["n_with_event"], "status": p["status"],
                "base": round(base, 4), "rr": round(rr, 2) if rr is not None else None,
                "y": y, "flagged_elevated": flagged_elevated, "flagged_absolute": flagged_absolute,
                "flagged_learned_live": False, "flagged_learned_blind": False,
                # planned-column features for the learned ranker (engines/hindsight_learned.py)
                "ok": 1 if p["status"] == "ok" else 0, "log_thick": math.log1p(thick), "lith": lith, "order": order,
                "td": w.td_md_m or 0.0, "n_offs": n_offs_doc,
            }
            if not light:
                cell["evidence"] = p["evidence"]
            cells.append(cell)
    return w, offs, ints, cells


def match_event(alert_index: dict[tuple[str | None, str], dict], formation: str | None, hazard: str, md_m: float) -> tuple[bool, float | None, dict | None]:
    """Pure matching rule, unit-testable without a DB: was there a live alert for this
    (formation, hazard) at the well's own depth, and how far ahead did it warn?"""
    a = alert_index.get((formation, hazard))
    if a is None or md_m is None:
        return False, None, None
    return True, round(md_m - a["alert_md_m"], 1), a


def _match_well_events(well_id: int, cells: list[dict], mode: str) -> tuple[list[dict], dict]:
    """Real trusted, depth-tagged events vs the cells flagged under `mode`. Also reports, per
    event, whether a naive own-source-base-rate>=absolute-threshold rule would have fired
    (secondary baseline for the forewarned-share metric — see baseline_lift_report for the
    primary, cell-based lift baseline)."""
    cx = ctx()
    thr = cfg()["hazard"]["alert_threshold"]
    flag_key = f"flagged_{mode}"
    alert_index = {(c["formation"], c["hazard"]): c for c in cells if c[flag_key]}
    cell_by_key = {(c["formation"], c["hazard"]): c for c in cells}
    trusted = [e for e in cx.events.get(well_id, []) if e.md_m is not None]
    events_out = []
    leads: list[float] = []
    n_forewarned = n_missed = n_baseline_forewarned = 0
    matched_keys: set[tuple[str | None, str]] = set()
    for e in sorted(trusted, key=lambda e: e.md_m):
        formation = e.formation or cx.tops.at(well_id, e.md_m)
        forewarned, lead_m, alert = match_event(alert_index, formation, e.hazard, e.md_m)
        if forewarned:
            n_forewarned += 1
            leads.append(lead_m)
            matched_keys.add((formation, e.hazard))
        else:
            n_missed += 1
        cell = cell_by_key.get((formation, e.hazard))
        baseline = bool(cell and cell["base"] >= thr)
        n_baseline_forewarned += baseline
        events_out.append({
            "event_id": e.id, "hazard": e.hazard, "label": taxonomy()["hazards"].get(e.hazard, {}).get("label", e.hazard),
            "md_m": e.md_m, "formation": formation, "formation_label": pretty(formation),
            "source_ref": e.source_ref, "evidence": e.evidence_span,
            "forewarned": forewarned, "lead_m": lead_m,
            "alert_ref": None if not alert else {"formation": alert["formation"], "hazard": alert["hazard"], "alert_md_m": alert["alert_md_m"],
                                                  "mean": alert["mean"], "base": alert["base"], "rr": alert["rr"], "n_eff": alert["n_eff"]},
            "baseline_forewarned": baseline,
        })
    n_alerts = sum(1 for c in cells if c[flag_key])
    n_alerts_with_event = len(matched_keys)
    summary = {
        "events": len(events_out), "forewarned": n_forewarned, "missed": n_missed,
        "median_lead_m": round(median(leads), 1) if leads else None, "leads_m": leads,
        "alerts": n_alerts, "alerts_with_event": n_alerts_with_event, "alerts_without_record": n_alerts - n_alerts_with_event,
        "baseline_forewarned": n_baseline_forewarned,
    }
    return events_out, summary


def run_well(well_id: int) -> dict:
    """Full blind-replay detail for one well: every cell walked, the alerts the configured mode
    would raise, the well's own trusted events matched against them, and the summary counts."""
    cx = ctx()
    if well_id not in cx.wells:
        raise KeyError(f"well {well_id} not found")
    hc = _hindsight_cfg()
    mode = hc["alert_mode"]
    w, offs, ints, cells = _cells_for_well(well_id, light=False)
    if mode in LEARNED_MODES:
        learned = (summary().get("learned") or {}).get("flags", {}).get(str(well_id), {})
        for c in cells:
            key = f"{c['formation']}|{c['hazard']}"
            for m in LEARNED_MODES:
                hit = (learned.get(m) or {}).get(key)
                c[f"flagged_{m}"] = hit is not None
                if hit is not None:
                    c[f"p_{m}"] = hit
    n_offsets_documented = sum(1 for o in offs if o["well_id"] in cx.documented)
    trusted = [e for e in cx.events.get(well_id, []) if e.md_m is not None]
    testable = w.lat is not None and bool(ints) and bool(trusted) and n_offsets_documented >= hc["min_offsets"]
    events_out, summ = _match_well_events(well_id, cells, mode)
    alerts = [c for c in cells if c[f"flagged_{mode}"]]
    alerts_other_mode = [c for c in cells if c[f"flagged_{_other_mode(mode)}"]]
    return {
        "well": {"id": w.id, "name": w.canonical_name, "field": w.field_name, "country": w.country, "source": w.source, "td_md_m": w.td_md_m},
        "alert_mode": mode, "testable": testable, "n_offsets": len(offs), "n_offsets_documented": n_offsets_documented,
        "formations": ints, "alerts": alerts, "n_alerts_other_mode": len(alerts_other_mode),
        "events": events_out, "summary": summ,
        "watchlist": _well_watchlist(cells, events_out, max(hc["watchlist_k"] or [5])),
    }


def _well_watchlist(cells: list[dict], events_out: list[dict], k: int) -> dict:
    """This well's blind top-k watch-list (by posterior mean) and which of its real problems were on it."""
    top = sorted(cells, key=_rank_key("mean"))[:k]
    on = {(c["formation"], c["hazard"]) for c in top}
    hits = sum(1 for e in events_out if (e["formation"], e["hazard"]) in on)
    return {"k": k, "hits": hits, "events": len(events_out),
            "items": [{k2: c[k2] for k2 in ("formation", "formation_label", "hazard", "label", "top_md_m", "alert_md_m", "mean", "ci", "n_eff", "base", "status")}
                      | {"has_event": any((e["formation"], e["hazard"]) == (c["formation"], c["hazard"]) for e in events_out)} for c in top]}


def _candidates(cx, max_wells: int | None) -> list[int]:
    """Deterministic sample: documented wells with >=1 trusted, depth-tagged event and formation
    tops, first N by id (None = every one — the default sample is now ALL testable wells)."""
    cand = sorted(
        wid for wid in cx.documented
        if cx.tops.tops(wid) and any(e.md_m is not None for e in cx.events.get(wid, []))
    )
    return cand if max_wells is None else cand[:max_wells]


def aggregate(rows: list[dict]) -> dict:
    """Roll a list of per-well `summary` dicts (as produced by run_well) into one headline
    (secondary metric: forewarned share / median lead)."""
    events = sum(r["events"] for r in rows)
    forewarned = sum(r["forewarned"] for r in rows)
    missed = sum(r["missed"] for r in rows)
    alerts = sum(r["alerts"] for r in rows)
    alerts_with_event = sum(r["alerts_with_event"] for r in rows)
    baseline_forewarned = sum(r["baseline_forewarned"] for r in rows)
    leads = [l for r in rows for l in r["leads_m"]]
    return {
        "n_wells": len(rows), "events": events, "forewarned": forewarned, "missed": missed,
        "forewarned_share": round(forewarned / events, 4) if events else None,
        "median_lead_m": round(median(leads), 1) if leads else None,
        "alerts": alerts, "alerts_with_event": alerts_with_event, "alerts_without_record": alerts - alerts_with_event,
        "alerts_with_event_share": round(alerts_with_event / alerts, 4) if alerts else None,
        "baseline_forewarned": baseline_forewarned,
        "baseline_forewarned_share": round(baseline_forewarned / events, 4) if events else None,
    }


# --------------------------------------------------------------------------------------------
# Primary metric: lift (recorded-event rate in flagged cells vs not), with a fair top-k-by-base-
# rate baseline. Wilson interval — same formula family as engines.ledger.wilson_lb, extended to
# both bounds (kept self-contained here rather than importing, since ledger.py belongs to USP2).
# --------------------------------------------------------------------------------------------

def wilson_ci(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(max(0.0, p * (1 - p) / n + z * z / (4 * n * n)))
    lo, hi = (center - margin) / denom, (center + margin) / denom
    return max(0.0, lo), min(1.0, hi)


def _lift_core(flagged: list[dict], unflagged: list[dict], z: float = 1.96) -> dict:
    nf, nu = len(flagged), len(unflagged)
    kf = sum(c["y"] for c in flagged)
    ku = sum(c["y"] for c in unflagged)
    rate_f = kf / nf if nf else None
    rate_u = ku / nu if nu else None
    lo_f, hi_f = wilson_ci(kf, nf, z) if nf else (None, None)
    lo_u, hi_u = wilson_ci(ku, nu, z) if nu else (None, None)
    lift = (rate_f / rate_u) if (rate_f is not None and rate_u) else None
    lift_ci = None
    if lo_f is not None and lo_u is not None and lo_u > 0:
        lift_ci = [round(lo_f / hi_u, 3) if hi_u > 0 else 0.0, round(hi_f / lo_u, 3)]
    note = None
    if nf == 0:
        note = "no cells were flagged by this rule"
    elif rate_u == 0:
        note = "the unflagged rate is zero, so lift cannot be estimated"
    elif lift_ci is None:
        note = "the interval could not be bounded (a rate hit the 0% edge)"
    elif lift_ci[0] <= 1.0 <= lift_ci[1]:
        note = "the approximate 95% interval for lift spans 1"
    elif lift is not None and abs(lift - 1) < 0.1:
        note = "lift is close to 1"
    no_measured = note is not None
    return {
        "n_flagged": nf, "k_flagged": kf, "rate_flagged": round(rate_f, 4) if rate_f is not None else None,
        "rate_flagged_ci": [round(lo_f, 4), round(hi_f, 4)] if nf else None,
        "n_unflagged": nu, "k_unflagged": ku, "rate_unflagged": round(rate_u, 4) if rate_u is not None else None,
        "rate_unflagged_ci": [round(lo_u, 4), round(hi_u, 4)] if nu else None,
        "lift": round(lift, 3) if lift is not None else None, "lift_ci_approx": lift_ci, "ci_level": z,
        "no_measured_lift_yet": no_measured, "note": note,
        "headline": "no measured lift yet" if no_measured else f"{round(lift, 2)}x lift",
    }


def lift_report(cells: list[dict], flag_key: str, z: float = 1.96) -> dict:
    """Split cells by cell[flag_key] and compare recorded-event rates."""
    flagged = [c for c in cells if c[flag_key]]
    unflagged = [c for c in cells if not c[flag_key]]
    return _lift_core(flagged, unflagged, z)


def baseline_lift_report(cells: list[dict], k: int, z: float = 1.96) -> dict:
    """Fair baseline: flag the same NUMBER of cells (k) as the model, chosen by base rate alone
    (top-k, ties broken deterministically), then compare rates the same way."""
    if k <= 0 or not cells:
        return _lift_core([], cells, z)
    ordered = sorted(cells, key=lambda c: (-c["base"], c["well_id"], c["formation"], c["hazard"]))
    return _lift_core(ordered[:k], ordered[k:], z)


def _stratify(cells: list[dict], wells_rows: list[dict], key: str, flag_key: str) -> dict:
    groups_c: dict[str, list] = defaultdict(list)
    for c in cells:
        groups_c[c[key] or "unknown"].append(c)
    groups_w: dict[str, list] = defaultdict(list)
    for w in wells_rows:
        groups_w[w[key] or "unknown"].append(w)
    out = {}
    for g in sorted(set(groups_c) | set(groups_w)):
        gc, gw = groups_c.get(g, []), groups_w.get(g, [])
        lr = lift_report(gc, flag_key)
        out[g] = {"n_wells": len(gw), "n_cells": len(gc), "lift": lr, "baseline": baseline_lift_report(gc, lr["n_flagged"]), "forewarned": aggregate(gw)}
    return out


def _rank_key(field: str):
    return lambda c: (-c[field], c["formation"] or "", c["hazard"])


def watchlist_report(cells: list[dict], events: list[tuple[int, str | None, str]], ks: list[int]) -> dict:
    """Per-well watch-list: rank each blind well's own (formation, hazard) cells and keep the top k.
    A real event is 'on the watch-list' when its (formation, hazard) cell is in its well's top k.
    Compared with ranking by the field base rate alone and with the exact expectation of a random
    pick of k cells (k / n_cells of that well, per event that has a cell)."""
    by_well: dict[int, list[dict]] = defaultdict(list)
    for c in cells:
        by_well[c["well_id"]].append(c)
    keys_by_well = {w: {(c["formation"], c["hazard"]) for c in cs} for w, cs in by_well.items()}
    n_events = len(events)
    rows = []
    for k in ks:
        top_model = {w: {(c["formation"], c["hazard"]) for c in sorted(cs, key=_rank_key("mean"))[:k]} for w, cs in by_well.items()}
        top_base = {w: {(c["formation"], c["hazard"]) for c in sorted(cs, key=_rank_key("base"))[:k]} for w, cs in by_well.items()}
        hit_m = sum(1 for w, f, h in events if (f, h) in top_model.get(w, set()))
        hit_b = sum(1 for w, f, h in events if (f, h) in top_base.get(w, set()))
        exp_r = sum(min(1.0, k / len(by_well[w])) for w, f, h in events if (f, h) in keys_by_well.get(w, set()))
        share_cells = sum(min(k, len(cs)) for cs in by_well.values()) / max(1, len(cells))
        rows.append({
            "k": k, "events": n_events, "hits": hit_m, "share": round(hit_m / n_events, 4) if n_events else None,
            "hits_ci": [round(x, 4) for x in wilson_ci(hit_m, n_events)] if n_events else None,
            "base_rate_hits": hit_b, "base_rate_share": round(hit_b / n_events, 4) if n_events else None,
            "random_expected": round(exp_r, 1), "random_share": round(exp_r / n_events, 4) if n_events else None,
            "x_random": round(hit_m / exp_r, 2) if exp_r else None,
            "share_of_cells_flagged": round(share_cells, 4),
        })
    return {"rows": rows, "n_events": n_events, "n_events_without_cell": sum(1 for w, f, h in events if (f, h) not in keys_by_well.get(w, set())),
            "method": ("For each blind well, its own formation x hazard cells are ranked by the blind posterior mean (offsets exclude the "
                       "well and its sidetracks); the top k form its watch-list. A recorded problem counts when its formation and hazard "
                       "are on that list. 'Random' is the exact expected hit count of picking k cells at random per well; 'base rate' "
                       "ranks by the field-wide (formation, hazard, source) rate alone. Problems whose formation is not in the well's "
                       "column can never be on a list and count as missed.")}


def operating_points(cells: list[dict], events: list[tuple[int, str | None, str]], thresholds: list[float]) -> list[dict]:
    """Sensitivity trade-off: at each posterior-mean threshold (with enough evidence), how many real
    problems were forewarned, how many cells were flagged, and how often a flag matched a record."""
    out = []
    for t in thresholds:
        flagged = {(c["well_id"], c["formation"], c["hazard"]) for c in cells if c["status"] == "ok" and c["mean"] >= t}
        for c in cells:
            c["_op"] = (c["well_id"], c["formation"], c["hazard"]) in flagged
        lr = lift_report(cells, "_op")
        fw = sum(1 for e in events if e in flagged)
        out.append({"threshold": t, "forewarned": fw, "events": len(events),
                    "forewarned_share": round(fw / len(events), 4) if events else None,
                    "flagged": lr["n_flagged"], "hit_rate": lr["rate_flagged"], "hit_rate_ci": lr["rate_flagged_ci"],
                    "lift": lr["lift"], "lift_ci_approx": lr["lift_ci_approx"], "no_measured_lift_yet": lr["no_measured_lift_yet"]})
    for c in cells:
        c.pop("_op", None)
    return out


def _fingerprint(cx) -> list[int]:
    n_events_depth = sum(1 for lst in cx.events.values() for e in lst if e.md_m is not None)
    n_tops = sum(len(cx.tops.penetrated(wid)) for wid in cx.documented)
    return [len(cx.wells), len(cx.documented), n_events_depth, n_tops]


LEARNED_METHOD = ("Alerts come from a learned ranker (gradient-boosted trees) trained on OTHER wells only: grouped 5-fold "
                  "cross-validation, where a well and every sidetrack of the same wellbore are always scored by a model that never "
                  "saw them. 'Live' adds the well's own reports, but only events recorded shallower than the alert point (layer "
                  "top minus the look-ahead distance) — what a rig would already know. The alert threshold is chosen on the "
                  "training wells for a fixed budget of alerts per well (hindsight.learned.alert_budget_per_well); the test "
                  "wells never set it. Assumption: the planned formation column equals the recorded one.")


def _learned(per_well: list[tuple], cx) -> dict | None:
    """Out-of-fold learned probabilities and flags for every testable well's cells (both variants).
    Sets cell['p_learned_*'] and cell['flagged_learned_*'] in place; returns per-well flag maps for run_well."""
    from app.engines import hindsight_learned as HL
    cells = [c for _, _, _, cs in per_well for c in cs]
    if len({wid for wid, *_ in per_well}) < 5 or not any(c["y"] for c in cells):
        return None
    lc = HL.learned_cfg()
    own = {wid: [(e.md_m, e.hazard) for e in cx.events.get(wid, []) if e.md_m is not None] for wid, *_ in per_well}
    HL.add_live_features(cells, own)
    groups = [cx.wells[c["well_id"]].parent_well or f"w{c['well_id']}" for c in cells]
    flags: dict[str, dict] = defaultdict(lambda: {m: {} for m in LEARNED_MODES})
    budgets = list(lc.get("budget_curve") or [])
    for mode, live in (("learned_blind", False), ("learned_live", True)):
        prob, flag, extra = HL.cross_validated(cells, groups, live, lc, budgets)
        for c, p, f in zip(cells, prob, flag):
            c[f"p_{mode}"] = float(p)
            c[f"flagged_{mode}"] = bool(f)
        for b, fl in extra.items():
            for c, f in zip(cells, fl):
                c.setdefault("_budget", {}).setdefault(mode, {})[b] = bool(f)
            if f:
                flags[str(c["well_id"])][mode][f"{c['formation']}|{c['hazard']}"] = round(float(p), 4)
    return {"config": {k: v for k, v in lc.items() if k != "watchlist_k"}, "flags": dict(flags), "budgets": budgets}


def _learned_metrics(per_well: list[tuple], cells: list[dict], events: list[tuple], hc: dict) -> dict:
    from app.engines import hindsight_learned as HL
    out: dict = {}
    n_wells = len(per_well)
    import numpy as np
    y = np.array([c["y"] for c in cells])
    wells = np.array([c["well_id"] for c in cells])
    n_h = len(taxonomy()["hazards"])
    out["auc"] = {m: HL.auc_with_ci(y, np.array([c[f"p_{m}"] for c in cells]), wells) for m in LEARNED_MODES}
    out["auc"]["field_average"] = HL.auc_with_ci(y, np.array([c["base"] for c in cells]), wells)
    out["auc"]["posterior"] = HL.auc_with_ci(y, np.array([c["mean"] for c in cells]), wells)
    out["hazard_in_layer_topk"] = {
        "learned_live": HL.hazard_in_layer_topk(cells, "p_learned_live", events, [1, 2, 3], n_h),
        "field_average": HL.hazard_in_layer_topk(cells, "base", events, [1, 2, 3], n_h),
    }
    curve = []
    budgets = sorted({b for c in cells for b in (c.get("_budget", {}).get("learned_live") or {})})
    for b in budgets:
        fl = {(c["well_id"], c["formation"], c["hazard"]) for c in cells if c["_budget"]["learned_live"][b]}
        layers = {(w, f) for w, f, _ in fl}
        fw = sum(1 for e in events if e in fl)
        lay = sum(1 for e in events if (e[0], e[1]) in layers)
        n_fl = len(fl)
        k_fl = sum(c["y"] for c in cells if c["_budget"]["learned_live"][b])
        curve.append({"budget_per_well": b, "alerts_per_well": round(n_fl / n_wells, 2) if n_wells else None,
                      "forewarned": fw, "forewarned_share": round(fw / len(events), 4) if events else None,
                      "layer_flagged": lay, "layer_flagged_share": round(lay / len(events), 4) if events else None,
                      "share_of_cells": round(n_fl / len(cells), 4) if cells else None,
                      "hit_rate": round(k_fl / n_fl, 4) if n_fl else None})
    out["budget_curve"] = curve
    for c in cells:
        c.pop("_budget", None)
    for mode in LEARNED_MODES:
        key = f"flagged_{mode}"
        lr = lift_report(cells, key)
        bl = baseline_lift_report(cells, lr["n_flagged"])
        rows = [_match_well_events(wid, cs, mode)[1] for wid, _, _, cs in per_well]
        fw = aggregate(rows)
        # fair baseline: same number of alerts, ranked by field base rate alone
        k = lr["n_flagged"]
        top = sorted(cells, key=lambda c: (-c["base"], c["well_id"], c["formation"] or "", c["hazard"]))[:k]
        top_keys = {(c["well_id"], c["formation"], c["hazard"]) for c in top}
        base_fw = sum(1 for e in events if e in top_keys)
        out[mode] = {
            "lift": lr, "baseline": bl, "forewarned": fw,
            "forewarned_ci": [round(x, 4) for x in wilson_ci(fw["forewarned"], fw["events"])] if fw["events"] else None,
            "alerts_per_well": round(lr["n_flagged"] / n_wells, 2) if n_wells else None,
            "baseline_forewarned": base_fw, "baseline_forewarned_share": round(base_fw / len(events), 4) if events else None,
            "watchlist": HL.watchlist_rows(cells, f"p_{mode}", events, hc["watchlist_k"]),
        }
    return out


_LOCK = threading.Lock()          # one computation at a time; concurrent callers wait for it instead of repeating it
_REFRESHING = threading.Event()   # set while a background refresh of a stale cache is running


def _read_cache() -> dict | None:
    try:
        return json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else None
    except (json.JSONDecodeError, OSError):
        return None


def _cache_ok(cached: dict | None, fp, n_wanted, hc) -> bool:
    return bool(cached) and (cached.get("engine_version") == ENGINE_VERSION and cached.get("fingerprint") == fp
                             and cached.get("max_wells_config") == n_wanted and cached.get("alert_mode_config") == hc["alert_mode"]
                             and cached.get("rr_min_config") == hc["rr_min"] and cached.get("learned_config") == hc["learned"])


def _refresh_in_background(max_wells: int | None) -> None:
    if _REFRESHING.is_set():
        return
    _REFRESHING.set()

    def run():
        try:
            summary(max_wells, force=True)
        finally:
            _REFRESHING.clear()
    threading.Thread(target=run, daemon=True, name="hindsight-refresh").start()


def summary(max_wells: int | None = None, force: bool = False, log=lambda *a: None) -> dict:
    """Cached blind-replay summary. A request never waits a minute for a recompute when an older
    result exists: the older result is returned (marked "stale": true) and a single background thread
    refreshes it. With no cache at all, callers share ONE computation under a lock."""
    cx = ctx()
    hc = _hindsight_cfg()
    n_wanted = max_wells if max_wells is not None else hc["max_wells"]
    fp = _fingerprint(cx)
    if not force:
        cached = _read_cache()
        if _cache_ok(cached, fp, n_wanted, hc):
            return cached
        if cached and cached.get("max_wells_config") == n_wanted:
            _refresh_in_background(max_wells)
            return {**cached, "stale": True}
    with _LOCK:
        if not force:
            cached = _read_cache()
            if _cache_ok(cached, fp, n_wanted, hc):
                return cached
        return _compute(max_wells, log)


def _compute(max_wells: int | None = None, log=lambda *a: None) -> dict:
    """Blind-replay lift over every documented, testable well (or `max_wells` of them, first-by-id).
    Written to data/processed/hindsight_summary.json, keyed by a DB fingerprint plus the config."""
    cx = ctx()
    hc = _hindsight_cfg()
    n_wanted = max_wells if max_wells is not None else hc["max_wells"]
    fp = _fingerprint(cx)
    t0 = time.perf_counter()
    candidates = _candidates(cx, n_wanted)
    mode = hc["alert_mode"]
    all_cells: list[dict] = []
    wells_out: list[dict] = []
    all_events: list[tuple[int, str | None, str]] = []
    per_well: list[tuple] = []
    for wid in candidates:
        w, offs, ints, cells = _cells_for_well(wid, light=True)  # offsets computed once per well, reused for every cell
        n_offs_doc = sum(1 for o in offs if o["well_id"] in cx.documented)
        trusted = [e for e in cx.events.get(wid, []) if e.md_m is not None]
        testable = w.lat is not None and bool(ints) and bool(trusted) and n_offs_doc >= hc["min_offsets"]
        if testable:
            per_well.append((wid, w, n_offs_doc, cells))
    learned_out = _learned(per_well, cx)
    for wid, w, n_offs_doc, cells in per_well:
        events_out, es = _match_well_events(wid, cells, mode)
        all_events.extend((wid, e["formation"], e["hazard"]) for e in events_out)
        wells_out.append({"well_id": wid, "name": w.canonical_name, "field": w.field_name, "country": w.country,
                          "source": w.source, "n_offsets": n_offs_doc, **es})
        all_cells.extend(cells)
    elapsed = round(time.perf_counter() - t0, 3)

    flag_key = f"flagged_{mode}"
    other_key = f"flagged_{_other_mode(mode)}"
    if learned_out:
        learned_out.update(_learned_metrics(per_well, all_cells, all_events, hc))
    model_lift = lift_report(all_cells, flag_key)
    baseline_lift = baseline_lift_report(all_cells, model_lift["n_flagged"])
    other_lift = lift_report(all_cells, other_key)
    other_baseline = baseline_lift_report(all_cells, other_lift["n_flagged"])

    out = {
        "engine_version": ENGINE_VERSION, "fingerprint": fp, "max_wells_config": n_wanted, "min_offsets_config": hc["min_offsets"],
        "alert_mode_config": mode, "rr_min_config": hc["rr_min"], "learned_config": hc["learned"],
        "n_candidates": len(candidates), "n_testable": len(wells_out), "n_cells": len(all_cells),
        "headline": model_lift["headline"],
        "lift": {"mode": mode, "model": model_lift, "baseline": baseline_lift},
        "lift_other_mode": {"mode": _other_mode(mode), "model": other_lift, "baseline": other_baseline},
        "learned": learned_out,
        "forewarned": aggregate(wells_out), "wells": wells_out,
        "watchlist": watchlist_report(all_cells, all_events, hc["watchlist_k"]),
        "operating_points": operating_points(all_cells, all_events, hc["operating_thresholds"]),
        "by_source": _stratify(all_cells, wells_out, "source", flag_key),
        "by_country": _stratify(all_cells, wells_out, "country", flag_key),
        "computed_in_s": elapsed, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": ((LEARNED_METHOD + " ") if mode in LEARNED_MODES else "") + ("Blind replay: for each documented well, every offset excludes the well itself and any well sharing "
                   "its parent_well (sidetracks). Each (well, formation, hazard) visited is a 'cell'. Rule "
                   f"'{mode}': " + ("the posterior's lower 80% bound is above the (formation, hazard, source) base rate "
                   "and mean/base >= hindsight.rr_min" if mode == "elevated" else ("the learned ranker's probability is above a threshold set on the training wells" if mode in LEARNED_MODES else "posterior mean >= hazard.alert_threshold"))
                   + ", with enough evidence (n_eff >= min_neff). Primary metric is LIFT: the recorded-event rate in "
                   "flagged cells vs unflagged cells (Wilson 95% interval on each; the lift interval is an approximate "
                   "ratio of those bounds). The baseline flags the same number of cells by base rate alone (top-k), so "
                   "lift is skill over 'just knowing the field average', not over guessing nothing. A flagged cell with "
                   "no matching real event is 'no recorded event' — not a false alarm, since these reports under-record "
                   "problems. Forewarned share and median lead distance (secondary) come from matching the well's own "
                   "trusted (needs_review=false), depth-tagged events against the alerts live in their formation."),
    }
    log(f"hindsight[{mode}]: n_testable={len(wells_out)}/{len(candidates)} cells={len(all_cells)} {model_lift['headline']} "
        f"(flagged n={model_lift['n_flagged']} rate={model_lift['rate_flagged']} vs unflagged rate={model_lift['rate_unflagged']}) "
        f"baseline={baseline_lift['headline']} forewarned_share={out['forewarned']['forewarned_share']} "
        f"median_lead_m={out['forewarned']['median_lead_m']} ({elapsed}s)")
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(out))
    except OSError:
        pass
    return out


def recompute(max_wells: int | None = None, log=print) -> dict:
    """Force a fresh computation (bootstrap / eval), bypassing the cache."""
    return summary(max_wells=max_wells, force=True, log=log)
