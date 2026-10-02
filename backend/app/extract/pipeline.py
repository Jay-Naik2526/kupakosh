"""Run extraction over all passages -> event + action rows (SPEC.md §9.1).

Pass 2 (LLM) is wired through app/llm/client.py but only runs when an API key is
configured; without one every row is method='rule' and the UI says so.
"""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import cfg
from app.db.models import Action, Activity, Document, Event, MudCheck, Passage, Well
from app.engines.formations import TopIndex
from app.extract.rules import extract_sentence, find_actions


def source_ref(doc: Document, p: Passage, well: Well) -> str:
    return f"doc:{doc.id}#{p.locator}"


def run(db: Session, log=print, kinds: tuple[str, ...] = ("WELL_HISTORY", "DDR_PDF", "DDR_XML", "DGH_REPORT", "AUDIT_REPORT", "SAFETY_ALERT",
                                                         "JUDGMENT", "PAPER", "BASIN_REPORT", "WCR_PDF", "EOWR_PDF",
                                                         "INCIDENT_REPORT"), doc_ids: set[int] | None = None) -> dict:
    """Full run (doc_ids=None) replaces all events/actions; an incremental run (upload) replaces only those of `doc_ids`."""
    c = cfg()["extract"]
    if doc_ids is None:
        db.execute(delete(Action))
        db.execute(delete(Event))
    else:
        pids = select(Passage.id).where(Passage.document_id.in_(doc_ids))
        db.execute(delete(Action).where(Action.passage_id.in_(pids)))
        db.execute(delete(Event).where(Event.passage_id.in_(pids)))
    db.flush()
    import re
    ctx_rx = re.compile(c["drilling_context"], re.I)
    planned_rx = re.compile(c["planned_intervention"], re.I) if c.get("planned_intervention") else None
    strong_rx = re.compile(c["strong_problem"], re.I) if c.get("strong_problem") else None
    planned_kinds = set(c.get("planned_review_kinds") or [])
    table_kinds = set(c.get("table_review_kinds") or [])
    tt = c.get("table_text") or {}
    tops = TopIndex(db)
    wells = {w.id: w for w in db.scalars(select(Well))}
    mud: dict[int, list[MudCheck]] = defaultdict(list)
    for m in db.scalars(select(MudCheck).order_by(MudCheck.well_id, MudCheck.md_m)):
        mud[m.well_id].append(m)

    act_by_passage = {a.passage_id: a for a in db.scalars(select(Activity)) if a.passage_id}
    n_ev = n_act = n_rev = n_dup = 0
    dq = select(Document).where(Document.kind.in_(kinds))
    if doc_ids is not None:
        dq = dq.where(Document.id.in_(doc_ids))
    docs = db.scalars(dq).all()
    for doc in docs:
        well = wells.get(doc.well_id)
        passages = db.scalars(select(Passage).where(Passage.document_id == doc.id).order_by(Passage.seq)).all()
        seen: list[tuple[str, float | None, int]] = []  # (hazard, md, seq) already emitted in this doc
        for p in passages:
            well = wells.get(p.well_id or doc.well_id)
            if well is None:
                continue  # Indian public documents: only sentences that name a well can yield events
            if doc.kind in c["context_required_kinds"] and not ctx_rx.search(p.text):
                continue  # incident text with no drilling context (injury, crane, equipment) is not a drilling hazard
            hits = extract_sentence(p.text, well.td_md_m if well else None)
            for h in hits:
                if _is_duplicate(seen, h.hazard, h.md_m, p.seq, c["dedup_depth_m"], cfg()["episodes"]["window_sentences"]):
                    n_dup += 1
                    continue
                seen.append((h.hazard, h.md_m, p.seq))
                formation = tops.at(well.id, h.md_m) if well else None
                conf = h.confidence + (c["conf_formation_bonus"] if formation else 0)
                if doc.ocr_mean_conf is not None:  # text read by OCR: scale by the document's mean word confidence (§9.1)
                    conf *= doc.ocr_mean_conf / 100
                mw, mw_src = h.mud_weight_ppg, "text" if h.mud_weight_ppg else None
                if mw is None and h.md_m is not None and well:
                    mw = _mud_at(mud[well.id], h.md_m, c["mud_table_max_gap_m"])
                    mw_src = "mud_table" if mw else None
                md = h.md_m if h.md_m is not None else p.md_m
                act = act_by_passage.get(p.id)
                if formation is None and well and md is not None:
                    formation = tops.at(well.id, md)
                if formation is None and act is not None and act.formation:
                    formation = act.formation  # no recorded tops for this well: use the formation the report line itself names
                # planned intervention work (P&A, completion, wireline) with no clearly stated problem: keep, but for review
                planned = (doc.kind in planned_kinds and planned_rx is not None and bool(planned_rx.search(p.text))
                           and not (strong_rx and strong_rx.search(p.text)))
                table_like = doc.kind in table_kinds and looks_like_table(p.text, tt)
                ev = Event(
                    well_id=well.id, passage_id=p.id, activity_id=act.id if act else None, hazard=h.hazard, md_m=md,
                    formation=formation, t=act.t_start if act else None, severity=h.severity, quantity=h.quantity, quantity_unit=h.quantity_unit,
                    mud_weight_ppg=mw, mud_weight_source=mw_src, confidence=round(min(conf, 1.0), 3),
                    method="rule", needs_review=conf < c["review_threshold"] or planned or table_like, evidence_span=p.text,
                    source_ref=source_ref(doc, p, well),
                )
                db.add(ev)
                n_ev += 1
                n_rev += ev.needs_review
            act = act_by_passage.get(p.id)
            for a, span in find_actions(p.text):
                db.add(Action(
                    well_id=well.id, passage_id=p.id, activity_id=act.id if act else None, action_type=a, detail=span,
                    md_m=p.md_m, t=act.t_start if act else None,
                    confidence=c["conf_rule_base"], source_ref=source_ref(doc, p, well),
                ))
                n_act += 1
    db.flush()
    log(f"extract: {n_ev} events ({n_rev} need review, {n_dup} duplicates merged), {n_act} action mentions")
    return {"events": n_ev, "needs_review": n_rev, "duplicates_merged": n_dup, "actions": n_act}


def looks_like_table(text: str, tt: dict) -> bool:
    """A line from a table or form rather than narrative: mostly number tokens, table bars, several all-caps form
    headers, or many "Field: value" pairs (only for long lines; real problem sentences are short)."""
    import re
    if not tt:
        return False
    toks = text.split()
    num = sum(1 for x in toks if re.fullmatch(r"[-+]?[\d.,/%°'\"]+[a-zA-Z]{0,3}", x)) / max(1, len(toks))
    caps = len(re.findall(r"\b[A-Z][A-Z()&/-]{3,}\b", text))
    return ((len(text) > tt["min_len"] and num > tt["num_token_share"]) or text.count("|") >= 2
            or (len(text) > tt["min_len"] and caps >= tt["caps_headers"])
            or (len(text) > tt["form_min_len"] and text.count(":") >= tt["form_colons"]))


def _is_duplicate(seen, hazard, md, seq, tol_m, window) -> bool:
    for hz, md0, seq0 in seen:
        if hz != hazard:
            continue
        if md is not None and md0 is not None and abs(md - md0) <= tol_m:
            return True
        if md is None and seq - seq0 <= window:
            return True  # a follow-up sentence about the same problem, no new depth
    return False


def _mud_at(rows: list[MudCheck], md: float, max_gap: float) -> float | None:
    if not rows:
        return None
    mds = [r.md_m for r in rows]
    i = bisect_left(mds, md)
    cands = [rows[j] for j in (i - 1, i) if 0 <= j < len(rows)]
    best = min(cands, key=lambda r: abs(r.md_m - md))
    return best.mw_ppg if abs(best.md_m - md) <= max_gap else None
