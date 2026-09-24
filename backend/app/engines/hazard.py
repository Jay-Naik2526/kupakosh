"""USP5: honest Bayesian hazard model (SPEC.md §9.5).

For an active location and formation F, each documented offset well i that penetrated F
gives y_i in {0,1} (a trusted event of hazard H recorded in F) with weight w_i = sim_i.
    prior      Beta(a0, b0), a0 = s * base, b0 = s * (1 - base)   (s = prior_strength)
    posterior  Beta(a0 + sum w_i y_i, b0 + sum w_i (1 - y_i))
    report     mean, central `ci` credible interval, n_eff = (sum w)^2 / sum w^2
If n_eff < min_neff -> status 'insufficient_evidence' (the numbers are still returned for audit
but the UI must not headline them).

Important limit: reports under-record problems, so y_i = 0 means "no problem recorded",
not "no problem happened". Probabilities are therefore rates of *recorded* problems.
"""
from __future__ import annotations

from functools import lru_cache

from scipy.stats import beta as beta_dist

from app.config import cfg, taxonomy
from app.engines.context import ctx


@lru_cache(maxsize=4096)
def base_rate(formation: str, hazard: str) -> tuple[float, int, str]:
    """Share of documented wells that penetrated `formation` with a recorded `hazard` there.
    Falls back to the hazard's rate across all formations when fewer than `base_min_wells` wells."""
    cx = ctx()
    c = cfg()["hazard"]
    wells = cx.penetrated.get(formation, set())
    if len(wells) >= c["base_min_wells"]:
        k = sum(1 for w in wells if (w, formation, hazard) in cx.ev_wf)
        return (k + 0.5) / (len(wells) + 1), len(wells), "formation"
    # all (well, formation) pairs
    n = sum(len(v) for v in cx.penetrated.values())
    k = sum(1 for (w, f, h) in cx.ev_wf if h == hazard)
    return (k + 0.5) / (n + 1), n, "all_formations"


def posterior(formation: str, hazard: str, offsets: list[dict]) -> dict:
    c = cfg()["hazard"]
    cx = ctx()
    base, base_n, base_scope = base_rate(formation, hazard)
    a0, b0 = c["prior_strength"] * base, c["prior_strength"] * (1 - base)
    sw = swy = sw2 = 0.0
    evidence = []
    for o in offsets:
        wid = o["well_id"]
        if wid not in cx.documented or formation not in cx.tops.penetrated(wid):
            continue
        w = o["sim"]
        if w <= 0:
            continue
        evs = cx.ev_wf.get((wid, formation, hazard), [])
        y = 1 if evs else 0
        sw += w
        sw2 += w * w
        swy += w * y
        evidence.append({"well_id": wid, "name": o["name"], "weight": round(w, 3), "y": y,
                         "distance_m": o["raw"]["distance_m"],
                         "events": [{"event_id": e.id, "md_m": e.md_m, "source_ref": e.source_ref} for e in evs]})
    a, b = a0 + swy, b0 + (sw - swy)
    n_eff = (sw * sw / sw2) if sw2 > 0 else 0.0
    lo_q = (1 - c["ci"]) / 2
    mean = a / (a + b)
    lo, hi = beta_dist.ppf([lo_q, 1 - lo_q], a, b)
    status = "ok" if n_eff >= c["min_neff"] else "insufficient_evidence"
    return {
        "formation": formation, "hazard": hazard, "label": taxonomy()["hazards"][hazard]["label"],
        "status": status, "mean": round(float(mean), 4), "ci": [round(float(lo), 4), round(float(hi), 4)], "ci_level": c["ci"],
        "n_eff": round(n_eff, 2), "n_wells": len(evidence), "n_with_event": sum(e["y"] for e in evidence),
        "prior": {"base_rate": round(base, 4), "base_n": base_n, "scope": base_scope, "a0": round(a0, 3), "b0": round(b0, 3)},
        "evidence": sorted(evidence, key=lambda e: (-e["y"], -e["weight"])),
    }


def profile(formations: list[str], offsets: list[dict]) -> list[dict]:
    hazards = list(taxonomy()["hazards"].keys())
    return [posterior(f, h, offsets) for f in formations for h in hazards]
