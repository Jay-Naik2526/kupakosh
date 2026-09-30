"""Look-ahead alerts for the replay (SPEC.md §9.7).

On each tick: current formation + formations starting within `lookahead_m` below the bit.
For every hazard with posterior mean >= alert_threshold (and enough evidence) -> alert.
Hazards with recorded offset events but insufficient evidence -> 'notice' (shown, not headlined).
Live anomaly matching a hazard expected in the current formation escalates the alert.
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session

from app.config import cfg, lithology
from app.engines import hazard as hz
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.ledger import ledger
from app.engines.offsets import offsets_for_well

ANOMALY_HAZARD = {"possible_losses": "lost_circulation", "possible_influx": "kick"}
CHANNEL_HAZARD = {"torque": ["torque_spike", "stuck_pipe"], "hookload": ["stuck_pipe"], "spp": ["wellbore_instability", "stuck_pipe"]}


@lru_cache(maxsize=64)
def _profile(well_id: int) -> tuple[list[dict], list[dict]]:
    offs = offsets_for_well(well_id)
    cx = ctx()
    tops = cx.tops.tops(well_id)
    forms = []
    for t in tops:
        if t.formation not in forms:
            forms.append(t.formation)
    return offs, [p for p in hz.profile(forms, offs)]


def formation_intervals(well_id: int) -> list[dict]:
    cx = ctx()
    out = []
    tops = cx.tops.tops(well_id)
    fm_mds = [x.top_md_m for x in tops if x.level == "FORMATION" and x.top_md_m is not None]
    for t in tops:
        # A GROUP is replaced by its FORMATION children only where they exist inside it. Groups with no
        # formation-level subdivision (e.g. shallow NORDLAND GP / HORDALAND GP on Sodir) stay in the column,
        # matching TopIndex.at(), which falls back to GROUP when no FORMATION covers a depth.
        base = t.base_md_m
        if t.level == "GROUP":
            lo, hi = t.top_md_m, t.base_md_m if t.base_md_m is not None else float("inf")
            if lo is None:
                continue
            inside = [m for m in fm_mds if lo <= m < hi]
            if inside:
                # Partly subdivided group: keep only its upper slice above the first formation child
                # (e.g. NORDLAND GP above UTSIRA FM), which TopIndex.at() also labels with the group.
                if min(inside) - lo < 1.0:
                    continue
                base = min(inside)
        out.append({"formation": t.formation, "label": pretty(t.formation), "top_md_m": t.top_md_m, "base_md_m": base,
                    "lithology": t.lithology or lithology().get(t.formation), "lithology_source": "report" if t.lithology else ("lexicon (approx.)" if t.formation in lithology() else None),
                    "source_ref": t.source_ref})
    return out


def assess(db: Session, well_id: int, bit_md: float, anomaly: dict | None = None, lookahead_m: float | None = None) -> dict:
    c = cfg()
    la = lookahead_m if lookahead_m is not None else c["lookahead"]["lookahead_m"]
    thr = c["hazard"]["alert_threshold"]
    offs, prof = _profile(well_id)
    ints = formation_intervals(well_id)
    current = next((i for i in ints if i["top_md_m"] <= bit_md and (i["base_md_m"] is None or bit_md < i["base_md_m"])), None)
    ahead = [i for i in ints if bit_md < i["top_md_m"] <= bit_md + la]
    targets = ([current] if current else []) + ahead
    alerts, notices = [], []
    offset_ids = [o["well_id"] for o in offs]
    for it in targets:
        dist = max(0.0, it["top_md_m"] - bit_md)
        for p in prof:
            if p["formation"] != it["formation"]:
                continue
            base = {"formation": it["formation"], "formation_label": it["label"], "distance_m": round(dist, 1),
                    "in_formation": it is current, **{k: p[k] for k in ("hazard", "label", "mean", "ci", "ci_level", "n_eff", "n_wells", "n_with_event", "status", "prior", "evidence")}}
            escalated = False
            if anomaly:
                sig_hz = ANOMALY_HAZARD.get(anomaly.get("signal") or "")
                ch_hz = {h for ch in anomaly.get("channels", []) for h in CHANNEL_HAZARD.get(ch, [])}
                escalated = it is current and (p["hazard"] == sig_hz or p["hazard"] in ch_hz) and p["n_with_event"] > 0
            if p["status"] == "ok" and p["mean"] >= thr:
                alerts.append({**base, "level": "escalated" if escalated else "alert", "fixes": _fixes(db, p["hazard"], it["formation"], offset_ids)})
            elif p["n_with_event"] > 0:
                notices.append({**base, "level": "escalated" if escalated else "notice", "fixes": _fixes(db, p["hazard"], it["formation"], offset_ids)})
    key = lambda a: ({"escalated": 0, "alert": 1, "notice": 2}[a["level"]], -a["mean"])
    return {"bit_md_m": bit_md, "current": current, "ahead": ahead, "alerts": sorted(alerts, key=key),
            "notices": sorted(notices, key=key), "n_offsets": len(offs), "anomaly": anomaly}


def _fixes(db: Session, hazard: str, formation: str, offset_ids: list[int]) -> dict:
    """Top ledger rows: formation+offsets first, then field-wide for the hazard, labelled with scope."""
    for scope, kw in (("offset wells, this formation", dict(formation=formation, well_ids=offset_ids)),
                      ("all records, this formation", dict(formation=formation)),
                      ("all records, this hazard", dict())):
        L = ledger(db, hazard, **kw)
        rows = [r for r in L["rows"] if r["n"] > 0]
        if rows:
            return {"scope": scope, "rows": rows[:3]}
    return {"scope": None, "rows": []}
