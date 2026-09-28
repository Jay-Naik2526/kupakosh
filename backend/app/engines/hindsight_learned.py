"""Learned alert ranker for the Hindsight test (round 3).

The Bayesian posterior alone (engines/hazard.py) flags very few layers, because recorded problem
rates per (formation, hazard) are low. This module learns, from OTHER wells only, which layer x hazard
cells tend to hold a recorded problem, and turns that into an alert policy with a fixed alert budget.

Two honest variants, both scored with grouped cross-validation (a well, and every sidetrack of the
same wellbore, is always in the test fold on its own — it never trains the model that scores it):

  * "blind"  — pre-drill: uses only other wells (posterior, base rate, evidence counts) plus the
               well's planned column (layer depth, thickness, order, lithology, planned TD).
               Assumption, stated in the method: the planned formation tops equal the recorded ones.
  * "live"   — while drilling: additionally uses the well's OWN reports, but only events recorded at
               depths shallower than the alert point (layer top - lookahead_m). Nothing below the
               alert point is visible, so it is causal.

Policy: one global probability threshold per fold, chosen on the TRAINING wells so that they get
`alert_budget_per_well` alerts on average (config hindsight.learned). The test wells are never used
to pick it. A fair baseline flags the same number of cells ranked by the field base rate alone.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from app.config import cfg

BLIND_NUM = ["mean", "base", "rr", "n_eff", "n_wells", "n_with_event", "ok", "log_thick", "top_md_m", "order", "td", "n_offs"]
LIVE_NUM = ["p_any", "p_same", "log_gap"]
CATS = ["hazard", "source", "lith"]


def learned_cfg() -> dict:
    c = (cfg().get("hindsight") or {}).get("learned") or {}
    return {
        "folds": c.get("folds", 5), "alert_budget_per_well": c.get("alert_budget_per_well", 6.0),
        "max_iter": c.get("max_iter", 300), "learning_rate": c.get("learning_rate", 0.05),
        "max_leaf_nodes": c.get("max_leaf_nodes", 15), "l2": c.get("l2", 1.0), "seed": c.get("seed", 0),
        "budget_curve": list(c.get("budget_curve", [6, 10, 15, 20])),
        "watchlist_k": list((cfg().get("hindsight") or {}).get("watchlist_k", [3, 5, 10])),
    }


def add_live_features(cells: list[dict], own_events: dict[int, list[tuple[float, str]]]) -> None:
    """own_events[well] = [(md_m, hazard), ...] (trusted, depth-tagged). Only events shallower than the
    cell's alert depth are counted — the part of the well already drilled when the alert fires."""
    for c in cells:
        prior = [e for e in own_events.get(c["well_id"], []) if e[0] < c["alert_md_m"]]
        c["p_any"] = len(prior)
        c["p_same"] = sum(1 for e in prior if e[1] == c["hazard"])
        last = max((e[0] for e in prior), default=None)
        c["log_gap"] = math.log1p(min(c["alert_md_m"] - last, 1e5)) if last is not None else math.log1p(1e5)


def _matrix(cells: list[dict], live: bool, cat_maps: dict) -> np.ndarray:
    cols = BLIND_NUM + (LIVE_NUM if live else [])
    rows = []
    for c in cells:
        r = [float(c.get(k) or 0.0) for k in cols]
        r += [float(cat_maps[k].get(str(c.get(k)), -1)) for k in CATS]
        rows.append(r)
    return np.array(rows, dtype=float)


def _threshold_for_budget(scores: np.ndarray, n_wells: int, budget: float) -> float:
    k = int(round(budget * n_wells))
    if k <= 0:
        return float("inf")
    if k >= len(scores):
        return float(scores.min())
    return float(np.sort(scores)[::-1][k - 1])


def cross_validated(cells: list[dict], groups: list, live: bool, lc: dict, budgets: list[float] | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Grouped K-fold out-of-fold probabilities, per-cell flags from a per-fold, training-only threshold at the
    configured budget, and (optionally) flags for other alert budgets — each threshold also set on training wells only."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import GroupKFold

    cat_maps = {k: {v: i for i, v in enumerate(sorted({str(c.get(k)) for c in cells}))} for k in CATS}
    X = _matrix(cells, live, cat_maps)
    y = np.array([c["y"] for c in cells])
    g = np.array(groups)
    well_of = np.array([c["well_id"] for c in cells])
    n_num = X.shape[1] - len(CATS)
    cat_mask = [False] * n_num + [True] * len(CATS)
    prob = np.zeros(len(cells))
    flag = np.zeros(len(cells), dtype=bool)
    extra = {b: np.zeros(len(cells), dtype=bool) for b in (budgets or [])}
    n_splits = min(lc["folds"], len(set(groups)))
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, g):
        m = HistGradientBoostingClassifier(max_iter=lc["max_iter"], learning_rate=lc["learning_rate"], max_leaf_nodes=lc["max_leaf_nodes"],
                                           l2_regularization=lc["l2"], categorical_features=cat_mask, random_state=lc["seed"])
        m.fit(X[tr], y[tr])
        p_tr = m.predict_proba(X[tr])[:, 1]
        thr = _threshold_for_budget(p_tr, len(set(well_of[tr])), lc["alert_budget_per_well"])
        prob[te] = m.predict_proba(X[te])[:, 1]
        flag[te] = prob[te] >= thr
        n_tr_wells = len(set(well_of[tr]))
        for b in extra:
            extra[b][te] = prob[te] >= _threshold_for_budget(p_tr, n_tr_wells, b)
    return prob, flag, extra


def watchlist_rows(cells: list[dict], score_key: str, events: list[tuple[int, str | None, str]], ks: list[int]) -> list[dict]:
    by_well: dict[int, list[dict]] = defaultdict(list)
    for c in cells:
        by_well[c["well_id"]].append(c)
    out = []
    for k in ks:
        top = {w: {(c["formation"], c["hazard"]) for c in sorted(cs, key=lambda c: (-c[score_key], c["formation"] or "", c["hazard"]))[:k]}
               for w, cs in by_well.items()}
        hits = sum(1 for w, f, h in events if (f, h) in top.get(w, set()))
        out.append({"k": k, "hits": hits, "events": len(events), "share": round(hits / len(events), 4) if events else None})
    return out


def auc_with_ci(y: np.ndarray, score: np.ndarray, wells: np.ndarray, n_boot: int = 200, seed: int = 0) -> dict:
    """ROC AUC with a 95% bootstrap interval that resamples WELLS (cells of one well stay together)."""
    from sklearn.metrics import roc_auc_score
    if len(set(y.tolist())) < 2:
        return {"auc": None, "ci": None}
    auc = float(roc_auc_score(y, score))
    uw = np.unique(wells)
    idx_by_w = {w: np.where(wells == w)[0] for w in uw}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        pick = np.concatenate([idx_by_w[w] for w in rng.choice(uw, size=len(uw), replace=True)])
        if len(set(y[pick].tolist())) == 2:
            boots.append(roc_auc_score(y[pick], score[pick]))
    ci = [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)] if boots else None
    return {"auc": round(auc, 3), "ci": ci}


def hazard_in_layer_topk(cells: list[dict], score_key: str, events: list[tuple[int, str | None, str]], ks: list[int], n_hazards: int) -> list[dict]:
    """For each real problem: within the layer where it happened, was its hazard among the top-k hazards
    ranked for that layer? Random pick would score k / n_hazards."""
    by_layer: dict[tuple, list[dict]] = defaultdict(list)
    for c in cells:
        by_layer[(c["well_id"], c["formation"])].append(c)
    out = []
    for k in ks:
        hits = 0
        for w, f, h in events:
            cs = by_layer.get((w, f))
            if cs and h in {c["hazard"] for c in sorted(cs, key=lambda c: (-c[score_key], c["hazard"]))[:k]}:
                hits += 1
        out.append({"k": k, "hits": hits, "events": len(events), "share": round(hits / len(events), 4) if events else None,
                    "random_share": round(min(1.0, k / n_hazards), 4)})
    return out
