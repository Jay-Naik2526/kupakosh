"""USP2 episode linker: event -> actions -> outcome (SPEC.md §9.2).

Two linking modes, chosen by what the source supports:
  * timed activities (DDR PDFs):  activities in (t_event, t_event + window_h]
  * narrative text (well history): the event sentence + the next `window_sentences`
    sentences of the same paragraph
The window closes early at a new event of the same hazard at a different depth.
Outcome = first outcome phrase in the window (rules); `outcome_ref` points to it.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import cfg
from app.db.models import Action, Activity, Document, Episode, Event, Passage
from app.extract.rules import _compiled, find_outcome, stated_npt_hours


def _after_trigger(text: str, hazard: str) -> str:
    """Part of the event sentence after the hazard keyword (so 'losses ... became total' counts, but
    words before the problem do not)."""
    hz, _, _ = _compiled()
    # the EARLIEST hazard mention in the sentence, not the first pattern in taxonomy order: in "Losses were
    # controlled by pumping lost circulation materials" the outcome follows "Losses were", not "lost circulation"
    ends = [m.end() for p in hz[hazard][0] if (m := p.search(text))]
    return text[min(ends):] if ends else text


def _anywhere(text: str) -> tuple[str, str] | None:
    """Outcome phrases that count wherever they sit in the event sentence (taxonomy outcome_anywhere)."""
    import re
    from app.config import taxonomy
    for k, pats in (taxonomy().get("outcome_anywhere") or {}).items():
        for pat in pats:
            m = re.search(pat, text, re.I)
            if m:
                return k, m.group(0)
    return None


import re as _re

PROGRESS = _re.compile(r"\b(drilled|drill(ing)? ahead|continued (drilling|to drill|to pooh|to rih|pooh|rih|running|to run)|pooh|rih|ran in|ran \d|tripped|pulled out|run in)\b[^.]{0,80}?\bto \d", _re.I)
SETBACK = _re.compile(r"\b(stuck|overpull|tight|pack(ed|ing)?[- ]?off|loss|losses|losing|kick|influx|fish|junk|stall|unable|could not|no go|fail|sidetrack|plug(ged)? back|cut)\w*", _re.I)


def _mentions(text: str, hazard: str) -> bool:
    hz, _, _ = _compiled()
    return any(p.search(text) for p in hz[hazard][0])


def _llm_cache():
    import json
    from app.config import DATA_DIR
    path = DATA_DIR / "processed" / "outcome_llm_cache.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (ValueError, OSError):
        data = {}
    return path, data


def run(db: Session, log=print, well_ids: set[int] | None = None, llm: bool = False, llm_refs: set[str] | None = None,
        llm_fill_only: bool = True) -> dict:
    """llm=True: also read each outcome with the local model (engines.outcome_llm), keeping the rule result when the
    model gives no verifiable answer. llm_refs limits the model to those event source refs (evaluation runs).
    Answers are cached by input text, so a re-run costs nothing."""
    """Full run, or (well_ids given) re-link only the episodes of those wells (used after an upload)."""
    c = cfg()["episodes"]
    eq = select(Event).order_by(Event.well_id, Event.passage_id)
    if well_ids is None:
        db.execute(delete(Episode))
    else:
        db.execute(delete(Episode).where(Episode.well_id.in_(well_ids)))
        eq = eq.where(Event.well_id.in_(well_ids))
    db.flush()
    events = db.scalars(eq).all()
    passages = {p.id: p for p in db.scalars(select(Passage).where(Passage.id.in_({e.passage_id for e in events if e.passage_id})))}
    doc_ids = {p.document_id for p in passages.values()}
    by_doc: dict[int, list[Passage]] = defaultdict(list)
    for p in db.scalars(select(Passage).where(Passage.document_id.in_(doc_ids)).order_by(Passage.seq)):
        by_doc[p.document_id].append(p)
    # timed sequences: all DDR activities of a well in time order (a window may cross into the next day's report)
    act_t = {a.passage_id: a.t_start for a in db.scalars(select(Activity)) if a.passage_id and a.t_start}
    by_well_timed: dict[int, list[Passage]] = defaultdict(list)
    for p in db.scalars(select(Passage).join(Document).where(Document.kind.in_(("DDR_PDF", "DDR_XML")))):
        if p.id in act_t:
            by_well_timed[p.well_id].append(p)
    for lst in by_well_timed.values():
        lst.sort(key=lambda p: act_t[p.id])
    acts_by_passage: dict[int, list[Action]] = defaultdict(list)
    for a in db.scalars(select(Action)):
        if a.passage_id:
            acts_by_passage[a.passage_id].append(a)
    events_by_passage: dict[int, list[Event]] = defaultdict(list)
    for e in events:
        events_by_passage[e.passage_id].append(e)

    counts = defaultdict(int)
    n_llm = n_llm_used = 0
    if llm:
        import hashlib
        import json
        from app.config import taxonomy
        from app.engines import outcome_llm
        cache_path, cache = _llm_cache()
        labels = {k: v.get("label", k) for k, v in taxonomy()["hazards"].items()}
    for ev in events:
        p0 = passages.get(ev.passage_id)
        if not p0:
            continue
        timed = ev.t is not None and p0.id in act_t
        seq = by_well_timed[ev.well_id] if timed else by_doc[p0.document_id]
        idx = next(i for i, p in enumerate(seq) if p.id == p0.id)
        para = p0.locator.split(".")[0]
        window = [p0]
        horizon = ev.t + timedelta(hours=c["window_h"]) if timed else None
        for p in seq[idx + 1: idx + 1 + c["window_sentences"]]:
            if timed:
                if act_t[p.id] > horizon:
                    break
            elif p.locator.split(".")[0] != para:
                break
            if any(e2.hazard == ev.hazard and e2.md_m is not None and ev.md_m is not None and abs(e2.md_m - ev.md_m) > cfg()["extract"]["dedup_depth_m"]
                   for e2 in events_by_passage.get(p.id, [])):
                break
            window.append(p)

        actions = [a for p in window for a in acts_by_passage.get(p.id, [])]
        outcome, oref, otext, hours = "unknown", None, None, None
        for i, p in enumerate(window):
            text = _after_trigger(p.text, ev.hazard) if i == 0 else p.text
            o = _anywhere(p0.text) if i == 0 else None
            o = o or find_outcome(text)
            if o:
                outcome, otext = o[0], p.text
                oref = f"doc:{p.document_id}#{p.locator}"
                if timed:
                    hours = (act_t[p.id] - ev.t).total_seconds() / 3600
                break
        if outcome == "unknown" and timed:
            # timed daily reports: when a later line shows normal progress (drilling / tripping to a depth) and does
            # not mention the problem again, the rig got past it — read as resolved (config episodes.progress_resolves)
            for p in window[1:]:
                if _mentions(p.text, ev.hazard):
                    break  # the problem is still being dealt with: no inference
                if PROGRESS.search(p.text) and not SETBACK.search(p.text):
                    outcome, otext = "resolved", p.text
                    oref = f"doc:{p.document_id}#{p.locator}"
                    hours = (act_t[p.id] - ev.t).total_seconds() / 3600
                    break
        method = "rule"
        # fill_only: the model is asked only where the rules found no outcome (rules are more precise where they fire)
        if llm and (llm_refs is None or ev.source_ref in llm_refs) and (outcome == "unknown" or not llm_fill_only):
            key = hashlib.sha256(json.dumps([ev.hazard] + [p.text for p in window]).encode()).hexdigest()
            if key not in cache:
                o_llm, quote, _ = outcome_llm.read_outcome(labels.get(ev.hazard, ev.hazard), [p.text for p in window])
                cache[key] = [o_llm, quote]
                n_llm += 1
                if n_llm % 50 == 0:
                    cache_path.write_text(json.dumps(cache))
                    log(f"episodes: local model read {n_llm} outcomes")
            o_llm, quote = cache[key]
            if o_llm is not None:
                n_llm_used += 1
                method = "local_llm"
                outcome, oref, otext, hours = o_llm, None, None, None
                if o_llm != "unknown":
                    q = outcome_llm._norm(quote).strip(" .\"'")
                    p_hit = next((p for p in window if q and q in outcome_llm._norm(p.text)), window[0])
                    oref, otext = f"doc:{p_hit.document_id}#{p_hit.locator}", p_hit.text
                    if timed and p_hit.id in act_t:
                        hours = (act_t[p_hit.id] - ev.t).total_seconds() / 3600
        npt = next((h for p in window if (h := stated_npt_hours(p.text)) is not None), None)
        # confidence: event confidence, reduced when the outcome had to be inferred from a later sentence
        conf = ev.confidence * (1.0 if outcome == "unknown" or oref == ev.source_ref else 0.85)
        db.add(Episode(
            well_id=ev.well_id, event_id=ev.id, hazard=ev.hazard, formation=ev.formation, md_m=ev.md_m,
            action_ids=[a.id for a in actions], action_types=sorted({a.action_type for a in actions}),
            outcome=outcome, outcome_ref=oref, outcome_text=otext, hours_to_resolve=round(hours, 2) if hours is not None and outcome in ("resolved", "partial") else None, npt_hours=npt,
            confidence=round(conf, 3), outcome_method=method,
        ))
        counts[outcome] += 1
    db.flush()
    if llm:
        cache_path.write_text(json.dumps(cache))
        log(f"episodes: local model answered {n_llm_used} (new calls {n_llm}); the rest keep the rule outcome")
    log(f"episodes: {sum(counts.values())} linked; outcomes {dict(counts)}")
    return dict(counts)
