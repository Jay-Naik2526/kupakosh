"""Shift-handover note, English or Hindi: one page the outgoing driller hands to the next shift.

Built only from what the other screens already compute, nothing new is estimated here:
  * where the bit is and which layers start within `handover.lookahead_m` below it (well's formation column);
  * "watch for": look-ahead alerts and notices (engines.lookahead.assess), each with probability, 80% range and
    the number of offset wells behind it, or "insufficient evidence";
  * "if it happens": the best-ranked fix from the outcome ledger, as "worked k of n";
  * one real offset-well report line per hazard, quoted with its source reference.
The plain-text version is short enough to paste into a chat message. Wording is template-based (no LLM), so a
number in the note is always the number the engine returned.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import cfg
from app.engines import lookahead
from app.engines.context import ctx

HAZ_HI = {
    "lost_circulation": "मड हानि (लॉस्ट सर्कुलेशन)", "kick": "किक / अंतर्वाह", "stuck_pipe": "पाइप अटकना",
    "torque_spike": "टॉर्क उछाल", "overpressure": "अति-दबाव / गैस", "cementing_issue": "सीमेंटिंग समस्या",
    "fishing": "फिशिंग / मलबा", "wellbore_instability": "कूप-भित्ति अस्थिरता",
}
ACT_EN = {
    "lcm_pill": "LCM pill", "reduce_mw": "reduce mud weight", "increase_mw": "raise mud weight", "reduce_flow": "reduce flow rate",
    "circulate_condition": "circulate and condition", "ream_backream": "ream / back-ream", "jar": "jarring", "spot_pill": "spot a pill",
    "pump_out": "pump out of hole", "cement_plug": "cement plug", "squeeze": "squeeze", "shut_in_kill": "shut in and kill",
    "pooh": "pull out of hole", "sidetrack": "sidetrack", "change_bha": "change BHA / bit", "fishing_run": "fishing run",
    "cut_and_abandon": "cut / back off", "other": "other",
}
ACT_HI = {
    "lcm_pill": "LCM पिल", "reduce_mw": "मड वज़न घटाना", "increase_mw": "मड वज़न बढ़ाना", "reduce_flow": "प्रवाह दर घटाना",
    "circulate_condition": "परिसंचरण व कंडीशनिंग", "ream_backream": "रीमिंग / बैक-रीमिंग", "jar": "जारिंग", "spot_pill": "पिल स्पॉट करना",
    "pump_out": "पंप करते हुए बाहर निकालना", "cement_plug": "सीमेंट प्लग", "squeeze": "स्क्वीज़", "shut_in_kill": "शट-इन व किल",
    "pooh": "पाइप बाहर निकालना (POOH)", "sidetrack": "साइडट्रैक", "change_bha": "BHA / बिट बदलना", "fishing_run": "फिशिंग रन",
    "cut_and_abandon": "काटना / बैक-ऑफ", "other": "अन्य",
}


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def _quote(db: Session, evidence: list[dict]) -> dict | None:
    """First offset well with a recorded event for this (layer, hazard): its report line and source ref."""
    from app.db.models import Event
    for ev in evidence:
        for e in ev.get("events") or []:
            row = db.get(Event, e["event_id"])
            if row is not None and row.evidence_span:
                return {"well": ev["name"], "md_m": e.get("md_m"), "text": row.evidence_span[:260], "source_ref": e["source_ref"]}
    return None


def build(db: Session, well_id: int, bit_md: float, lang: str = "en") -> dict:
    cx = ctx()
    if well_id not in cx.wells:
        raise KeyError(well_id)
    hc = cfg().get("handover") or {}
    la = float(hc.get("lookahead_m", 500))
    w = cx.wells[well_id]
    a = lookahead.assess(db, well_id, bit_md, lookahead_m=la)
    hi = lang == "hi"
    items = []
    for x in (a["alerts"] + a["notices"])[: int(hc.get("max_hazards", 4))]:
        rows = [r for r in (x.get("fixes") or {}).get("rows", []) if r["n"] > 0]
        fix = next((r for r in rows if not r["anecdotal"]), rows[0] if rows else None)  # a fix with >= 3 cases before an anecdote
        items.append({
            "hazard": x["hazard"], "label": HAZ_HI.get(x["hazard"], x["label"]) if hi else x["label"],
            "formation": x["formation_label"], "distance_m": x["distance_m"], "in_formation": x["in_formation"],
            "level": x["level"], "status": x["status"], "mean": x["mean"], "ci": x["ci"], "n_eff": x["n_eff"], "n_with_event": x["n_with_event"],
            "fix": None if not fix else {"action": fix["action"], "label": (ACT_HI if hi else ACT_EN).get(fix["action"], fix["action"]),
                                         "k": fix["k"], "n": fix["n"], "anecdotal": fix["anecdotal"], "median_hours": fix["median_hours"],
                                         "scope": (x.get("fixes") or {}).get("scope")},
            "offset_line": _quote(db, x.get("evidence") or []),
        })
    cur = a["current"]
    ahead = [{"formation": i["label"], "top_md_m": i["top_md_m"], "distance_m": round(i["top_md_m"] - bit_md, 1)} for i in a["ahead"]]
    return {
        "well": {"id": w.id, "name": w.canonical_name, "field": w.field_name, "country": w.country},
        "bit_md_m": bit_md, "lookahead_m": la, "lang": "hi" if hi else "en",
        "current": None if not cur else {"formation": cur["label"], "top_md_m": cur["top_md_m"]},
        "ahead": ahead, "items": items, "n_offsets": a["n_offsets"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "text": _text(w.canonical_name, bit_md, la, cur, ahead, items, a["n_offsets"], hi),
    }


def _text(name, bit_md, la, cur, ahead, items, n_offs, hi: bool) -> str:
    """Plain text for a chat message. Every figure comes from `items` / `ahead`."""
    L = []
    if hi:
        L.append(f"शिफ्ट हैंडओवर · {name} · बिट {round(bit_md)} m MD")
        L.append(f"वर्तमान परत: {cur['label'] if cur else 'अज्ञात'}")
        L.append("अगले " + f"{round(la)} m में परतें: " + (", ".join(f"{x['formation']} ({round(x['distance_m'])} m में)" for x in ahead) or "कोई नई परत नहीं"))
        L.append("ध्यान रखें:")
        for i, x in enumerate(items, 1):
            where = "इसी परत में" if x["in_formation"] else f"{x['formation']}, {round(x['distance_m'])} m आगे"
            p = (f"{_pct(x['mean'])} (सीमा {_pct(x['ci'][0])}–{_pct(x['ci'][1])}, {x['n_eff']:.1f} कूपों का प्रमाण)" if x["status"] == "ok"
                 else f"अपर्याप्त प्रमाण ({x['n_with_event']} निकट कूपों में दर्ज)")
            L.append(f"{i}. {x['label']} — {where} — {p}")
            if x["fix"]:
                f = x["fix"]
                L.append(f"   पहले क्या काम आया: {f['label']} — {f['n']} में से {f['k']:g} बार" + (" (कम उदाहरण)" if f["anecdotal"] else ""))
        if not items:
            L.append("इस दूरी में निकट कूपों में कोई दर्ज समस्या नहीं।")
        L.append(f"आधार: {n_offs} निकट कूप · केवल निर्णय सहायता, निर्णय अभियंता का।")
    else:
        L.append(f"Shift handover · {name} · bit {round(bit_md)} m MD")
        L.append(f"Current layer: {cur['label'] if cur else 'unknown'}")
        L.append(f"Layers in the next {round(la)} m: " + (", ".join(f"{x['formation']} (in {round(x['distance_m'])} m)" for x in ahead) or "no new layer"))
        L.append("Watch for:")
        for i, x in enumerate(items, 1):
            where = "in this layer" if x["in_formation"] else f"{x['formation']}, {round(x['distance_m'])} m ahead"
            p = (f"{_pct(x['mean'])} (range {_pct(x['ci'][0])}–{_pct(x['ci'][1])}, evidence {x['n_eff']:.1f} wells)" if x["status"] == "ok"
                 else f"insufficient evidence (recorded in {x['n_with_event']} nearby wells)")
            L.append(f"{i}. {x['label']} — {where} — {p}")
            if x["fix"]:
                f = x["fix"]
                L.append(f"   What worked before: {f['label']} — {f['k']:g} of {f['n']}" + (" (anecdotal)" if f["anecdotal"] else ""))
        if not items:
            L.append("No recorded problem in nearby wells within this distance.")
        L.append(f"Based on {n_offs} nearby wells · decision support only, the engineer decides.")
    return "\n".join(L)

