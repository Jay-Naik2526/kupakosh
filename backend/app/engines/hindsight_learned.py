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

Round 4 (accuracy): the model is no longer one fixed tree configuration. Each outer fold picks, using an
INNER grouped cross-validation on its own training wells only, between (a) the single model, (b) an
ensemble that averages three tree configurations, and (c) that ensemble plus "layer context" features
(the blind posterior of the same hazard in the layer above and below, and the hazard's rank inside its
layer — all computed from other wells). The outer test wells never influence the choice, so the reported
numbers are nested-cross-validation numbers, not the best of several tries.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from app.config import cfg

BLIND_NUM = ["mean", "base", "rr", "n_eff", "n_wells", "n_with_event", "ok", "log_thick", "top_md_m", "order", "td", "n_offs"]
LIVE_NUM = ["p_any", "p_same", "log_gap"]
CTX_NUM = ["m_up", "m_dn", "b_up", "h_rank", "h_share"]  # layer context, from other wells only (add_context_features)
CATS = ["hazard", "source", "lith"]


def learned_cfg() -> dict:
    c = (cfg().get("hindsight") or {}).get("learned") or {}
    return {
        "folds": c.get("folds", 5), "alert_budget_per_well": c.get("alert_budget_per_well", 6.0),
        "max_iter": c.get("max_iter", 300), "learning_rate": c.get("learning_rate", 0.05),
        "max_leaf_nodes": c.get("max_leaf_nodes", 15), "l2": c.get("l2", 1.0), "seed": c.get("seed", 0),
        "budget_curve": list(c.get("budget_curve", [6, 10, 15, 20])),
        "members": list(c.get("members") or [{}]),       # ensemble members: parameter overrides of the base model
        "candidates": list(c.get("candidates") or ["single"]),  # chosen per outer fold by inner CV: single | ensemble | ensemble_ctx
        "inner_folds": c.get("inner_folds", 4),
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


def add_context_features(cells: list[dict]) -> None:
    """Layer context for each cell, from the blind posteriors of the SAME well's other cells (so from other
    wells only): the hazard's posterior in the layer above and below, the base rate above, and the hazard's
    rank and share inside its own layer."""
    by_pos: dict[int, dict] = defaultdict(dict)
    by_layer: dict[tuple, list[dict]] = defaultdict(list)
    for c in cells:
        by_pos[c["well_id"]][(c["order"], c["hazard"])] = c
        by_layer[(c["well_id"], c["formation"])].append(c)
    for c in cells:
        d = by_pos[c["well_id"]]
        up, dn = d.get((c["order"] - 1, c["hazard"])), d.get((c["order"] + 1, c["hazard"]))
        c["m_up"] = up["mean"] if up else -1.0
        c["m_dn"] = dn["mean"] if dn else -1.0
        c["b_up"] = up["base"] if up else -1.0
    for cs in by_layer.values():
        tot = sum(c["mean"] for c in cs) or 1.0
        for i, c in enumerate(sorted(cs, key=lambda c: (-c["mean"], c["hazard"]))):
            c["h_rank"] = i
            c["h_share"] = c["mean"] / tot


def _matrix(cells: list[dict], live: bool, cat_maps: dict, ctx_feats: bool = False) -> np.ndarray:
    cols = BLIND_NUM + (LIVE_NUM if live else []) + (CTX_NUM if ctx_feats else [])
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


def _fit_predict(X: np.ndarray, y: np.ndarray, tr: np.ndarray, te_sets: list[np.ndarray], cat_mask: list[bool], lc: dict, members: list[dict]) -> list[np.ndarray]:
    """Fit every ensemble member on rows `tr`; return the mean predicted probability for each index set."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    outs = [np.zeros(len(t)) for t in te_sets]
    for mem in members:
        p = {**lc, **mem}
        m = HistGradientBoostingClassifier(max_iter=p["max_iter"], learning_rate=p["learning_rate"], max_leaf_nodes=p["max_leaf_nodes"],
                                           l2_regularization=p["l2"], categorical_features=cat_mask, random_state=p["seed"])
        m.fit(X[tr], y[tr])
        for o, t in zip(outs, te_sets):
            o += m.predict_proba(X[t])[:, 1] / len(members)
    return outs


def _candidate(name: str, lc: dict) -> tuple[list[dict], bool]:
    if name == "single":
        return [{}], False
    return lc["members"], name == "ensemble_ctx"


def cross_validated(cells: list[dict], groups: list, live: bool, lc: dict, budgets: list[float] | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Grouped K-fold out-of-fold probabilities, per-cell flags from a per-fold, training-only threshold at the
    configured budget, and (optionally) flags for other alert budgets — each threshold also set on training wells only.
    When several candidates are configured, each outer fold picks one by an inner grouped CV on its training wells."""
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import GroupKFold

    cat_maps = {k: {v: i for i, v in enumerate(sorted({str(c.get(k)) for c in cells}))} for k in CATS}
    cands = lc.get("candidates") or ["single"]
    if any(c != "single" for c in cands) and "h_rank" not in cells[0]:
        add_context_features(cells)
    Xs = {ctx_f: _matrix(cells, live, cat_maps, ctx_f) for ctx_f in {_candidate(c, lc)[1] for c in cands}}
    y = np.array([c["y"] for c in cells])
    g = np.array(groups)
    well_of = np.array([c["well_id"] for c in cells])
    prob = np.zeros(len(cells))
    flag = np.zeros(len(cells), dtype=bool)
    extra = {b: np.zeros(len(cells), dtype=bool) for b in (budgets or [])}
    chosen: list[str] = []
    n_splits = min(lc["folds"], len(set(groups)))
    for tr, te in GroupKFold(n_splits=n_splits).split(Xs[next(iter(Xs))], y, g):
        best = cands[0]
        if len(cands) > 1:  # inner CV on the training wells only
            scores = {}
            for name in cands:
                members, ctx_f = _candidate(name, lc)
                X = Xs[ctx_f]
                oof = np.zeros(len(tr))
                for itr, ite in GroupKFold(n_splits=lc.get("inner_folds", 4)).split(X[tr], y[tr], g[tr]):
                    oof[ite] = _fit_predict(X[tr], y[tr], itr, [ite], [False] * (X.shape[1] - len(CATS)) + [True] * len(CATS), lc, members)[0]
                scores[name] = roc_auc_score(y[tr], oof) if len(set(y[tr].tolist())) == 2 else 0.0
            best = max(cands, key=lambda n: (scores[n], -cands.index(n)))
        chosen.append(best)
        members, ctx_f = _candidate(best, lc)
        X = Xs[ctx_f]
        cat_mask = [False] * (X.shape[1] - len(CATS)) + [True] * len(CATS)
        p_tr, p_te = _fit_predict(X, y, tr, [tr, te], cat_mask, lc, members)
        n_tr_wells = len(set(well_of[tr]))
        thr = _threshold_for_budget(p_tr, n_tr_wells, lc["alert_budget_per_well"])
        prob[te] = p_te
        flag[te] = p_te >= thr
        for b in extra:
            extra[b][te] = p_te >= _threshold_for_budget(p_tr, n_tr_wells, b)
    cross_validated.last_choice = chosen  # which candidate each outer fold picked (reported in the summary)
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
