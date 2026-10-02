"""Preventable repeats: how often a real problem had ALREADY been recorded, in the same layer, in an older nearby well.

For every trusted, layer-tagged problem in the records: look at the offset wells of that well (same radius and
similarity rules as everywhere else; the well's own sidetracks excluded) that were spudded BEFORE it. If one of them
has a recorded problem of the same hazard in the same layer, the problem is a "repeat": the knowledge existed in a
report before this well was drilled. That is the gap Kupakosh closes, measured on real records.

Honest reading:
  * A repeat does not prove the problem was preventable. It shows a warning was available in the records.
  * Records under-report problems, so the true repeat share is probably higher, not lower.
  * Counted per (well, layer, hazard), so one long problem written in many lines counts once.
"""
from __future__ import annotations

import math
from collections import defaultdict

from app.config import taxonomy
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.hindsight import _family, wilson_ci
from app.engines.offsets import offsets_for_well

_CACHE: dict = {}


def summary(force: bool = False) -> dict:
    """In memory per context, and on disk keyed by the database fingerprint, so a server restart answers at once."""
    import json
    from app.config import DATA_DIR
    from app.engines.hindsight import _fingerprint
    cx = ctx()
    if not force and _CACHE.get("cx") is cx:
        return _CACHE["out"]
    path = DATA_DIR / "processed" / "repeats_summary.json"
    fp = _fingerprint(cx)
    if not force and path.exists():
        try:
            disk = json.loads(path.read_text())
            if disk.get("fingerprint") == fp:
                _CACHE.update(cx=cx, out=disk["out"])
                return disk["out"]
        except (ValueError, OSError, KeyError):
            pass
    out = _compute(cx)
    try:
        path.write_text(json.dumps({"fingerprint": fp, "out": out}))
    except OSError:
        pass
    return out


def _compute(cx) -> dict:
    labels = {k: v.get("label", k) for k, v in taxonomy()["hazards"].items()}
    # first recorded event per (well, formation, hazard), from written records only
    first: dict[tuple, object] = {}
    for key, evs in cx.ev_wf_records.items():
        first[key] = min(evs, key=lambda e: (e.md_m is None, e.md_m or 0))
    by_well = defaultdict(list)
    for (w, f, h), e in first.items():
        by_well[w].append((f, h, e))
    # wider view: the same hazard in the same layer recorded in ANY earlier-spudded well of the archive (any distance)
    hist: dict[tuple[str, str], list] = defaultdict(list)
    for (w2, f2, h2) in first:
        if cx.wells[w2].spud_date:
            hist[(f2, h2)].append(cx.wells[w2].spud_date)
    n_any = k_any = 0
    n = k = 0
    by_h: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_decade: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    gaps_years: list[float] = []
    examples = []
    for wid, items in by_well.items():
        w = cx.wells[wid]
        if w.spud_date is None or w.lat is None:
            continue
        fam = _family(wid)
        earlier = [o for o in offsets_for_well(wid, documented_only=True) if o["well_id"] not in fam and cx.wells[o["well_id"]].spud_date
                   and cx.wells[o["well_id"]].spud_date < w.spud_date]
        for f, h, e in items:
            prior = [o for o in earlier if (o["well_id"], f, h) in cx.ev_wf_records]
            n_any += 1
            k_any += any(d < w.spud_date for d in hist.get((f, h), []))
            n += 1
            by_h[h][1] += 1
            dec = w.spud_date.year // 10 * 10
            by_decade[dec][1] += 1
            if not prior:
                continue
            k += 1
            by_h[h][0] += 1
            by_decade[dec][0] += 1
            o = min(prior, key=lambda o: cx.wells[o["well_id"]].spud_date)  # the first warning on record
            ow = cx.wells[o["well_id"]]
            pe = first.get((o["well_id"], f, h)) or cx.ev_wf_records[(o["well_id"], f, h)][0]
            gap = (w.spud_date - ow.spud_date).days / 365.25
            gaps_years.append(gap)
            examples.append({"well": w.canonical_name, "spud": w.spud_date.isoformat(), "hazard": h, "label": labels.get(h, h),
                             "formation": pretty(f), "md_m": e.md_m, "source_ref": e.source_ref, "evidence": (e.evidence_span or "")[:240],
                             "earlier_well": ow.canonical_name, "earlier_spud": ow.spud_date.isoformat(),
                             "earlier_distance_m": o["raw"]["distance_m"], "years_before": round(gap, 1),
                             "earlier_source_ref": pe.source_ref, "earlier_evidence": (pe.evidence_span or "")[:240],
                             "n_earlier_wells": len({p["well_id"] for p in prior})})
    lo, hi = wilson_ci(k, n) if n else (None, None)
    gaps_years.sort()
    lo_a, hi_a = wilson_ci(k_any, n_any) if n_any else (None, None)
    out = {
        "archive": {"problems": n_any, "repeats": k_any, "share": round(k_any / n_any, 4) if n_any else None,
                    "share_ci": [round(lo_a, 4), round(hi_a, 4)] if n_any else None,
                    "method": "same hazard already recorded in the same layer in any earlier-spudded well of the archive, any distance"},
        "problems": n, "repeats": k, "share": round(k / n, 4) if n else None,
        "share_ci": [round(lo, 4), round(hi, 4)] if n else None,
        "median_years_warning_existed": round(gaps_years[len(gaps_years) // 2], 1) if gaps_years else None,
        "by_hazard": sorted(({"hazard": h, "label": labels.get(h, h), "repeats": a, "problems": b, "share": round(a / b, 4) if b else None}
                             for h, (a, b) in by_h.items()), key=lambda r: -r["problems"]),
        "by_decade": [{"decade": d, "repeats": a, "problems": b, "share": round(a / b, 4) if b else None}
                      for d, (a, b) in sorted(by_decade.items())],
        # most striking first: the warning sat in the records longest, from a close well
        "examples": sorted(examples, key=lambda x: (-x["n_earlier_wells"], -x["years_before"]))[:8],
        "method": ("Each recorded problem (one per well, layer and hazard, written records only) is checked against the offset "
                   "wells of its well that were spudded earlier (same radius and similarity rules as the rest of the app; the "
                   "well's own sidetracks excluded). It is a repeat when one of them had already recorded the same hazard in the "
                   "same layer. A repeat shows the warning existed in a report; it does not prove the problem was preventable. "
                   "Reports under-record problems, so the true share is likely higher."),
    }
    _CACHE.update(cx=cx, out=out)
    return out
