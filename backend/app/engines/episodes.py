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
    for p in hz[hazard][0]:
        m = p.search(text)
        if m:
            return text[m.end():]
    return text


def run(db: Session, log=print, well_ids: set[int] | None = None) -> dict:
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
            o = find_outcome(text)
            if o:
                outcome, otext = o[0], p.text
                oref = f"doc:{p.document_id}#{p.locator}"
                if timed:
                    hours = (act_t[p.id] - ev.t).total_seconds() / 3600
                break
        npt = next((h for p in window if (h := stated_npt_hours(p.text)) is not None), None)
        # confidence: event confidence, reduced when the outcome had to be inferred from a later sentence
        conf = ev.confidence * (1.0 if outcome == "unknown" or oref == ev.source_ref else 0.85)
        db.add(Episode(
            well_id=ev.well_id, event_id=ev.id, hazard=ev.hazard, formation=ev.formation, md_m=ev.md_m,
            action_ids=[a.id for a in actions], action_types=sorted({a.action_type for a in actions}),
            outcome=outcome, outcome_ref=oref, outcome_text=otext, hours_to_resolve=round(hours, 2) if hours is not None and outcome in ("resolved", "partial") else None, npt_hours=npt,
            confidence=round(conf, 3),
        ))
        counts[outcome] += 1
    db.flush()
    log(f"episodes: {sum(counts.values())} linked; outcomes {dict(counts)}")
    return dict(counts)
