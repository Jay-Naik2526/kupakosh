"""Evaluations (SPEC.md §16). Results go to eval_result and appear on the Accuracy page.

A missing gold file -> the metric is simply not written, and the UI shows "Not evaluated".
Gold labels in data/eval/ were made on real report lines; the `labeller` column says who
labelled them (currently an AI assistant, pending human verification — shown in the notes).
"""
from __future__ import annotations

import csv
import random
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import EVAL_DIR, cfg, taxonomy
from app.db.models import Episode, EvalResult, Event, Passage
from app.engines import hazard as hz
from app.engines.context import ctx, reset
from app.engines.offsets import offsets_for_well


def _labeller_note(rows: list[dict]) -> str:
    who = {r.get("labeller", "") for r in rows}
    return "labels: " + "; ".join(sorted(w for w in who if w))


def extraction(db: Session) -> list[EvalResult]:
    p = EVAL_DIR / "events_gold.csv"
    if not p.exists():
        return []
    rows = list(csv.DictReader(p.open()))
    tol = cfg()["auditor"]["depth_tol_m"]
    tp = fp = fn = 0
    d_ok = d_n = 0
    for r in rows:
        true = {h for h in r["true_hazards"].split(";") if h}
        evs = db.scalars(select(Event).where(Event.passage_id == int(r["passage_id"]))).all()
        pred = {e.hazard for e in evs}
        tp += len(pred & true)
        fp += len(pred - true)
        fn += len(true - pred)
        if r["true_md_m"]:
            for e in evs:
                if e.hazard in true and e.md_m is not None:
                    d_n += 1
                    d_ok += abs(e.md_m - float(r["true_md_m"])) <= tol
    note = f"{len(rows)} report lines (35 with an extracted event, 15 keyword lines without); {_labeller_note(rows)}"
    return [
        EvalResult(name="extraction", metric="event precision", value=tp / (tp + fp) if tp + fp else None, n=tp + fp, notes=note),
        EvalResult(name="extraction", metric="event recall", value=tp / (tp + fn) if tp + fn else None, n=tp + fn, notes=note),
        EvalResult(name="extraction", metric="depth within tolerance", value=d_ok / d_n if d_n else None, n=d_n, notes=f"±{tol} m; {note}"),
    ]


def episodes(db: Session) -> list[EvalResult]:
    p = EVAL_DIR / "episodes_gold.csv"
    if not p.exists():
        return []
    rows = list(csv.DictReader(p.open()))
    by = {}
    for ep, ev in db.execute(select(Episode, Event).join(Event, Event.id == Episode.event_id)):
        by[(ev.source_ref, ep.hazard)] = ep.outcome
    correct = n = known_ok = known_n = not_ep = 0
    for r in rows:
        pred = by.get((r["event_source_ref"], r["hazard"]))
        if pred is None:
            continue
        if r["true_outcome"] == "n/a":
            not_ep += 1
            continue
        n += 1
        correct += pred == r["true_outcome"]
        if pred != "unknown":
            known_n += 1
            known_ok += pred == r["true_outcome"]
    note = f"{len(rows)} sampled episodes; {not_ep} were not real problem episodes (extraction errors) and are excluded; {_labeller_note(rows)}"
    return [
        EvalResult(name="episodes", metric="outcome precision", value=known_ok / known_n if known_n else None, n=known_n, notes="among episodes where an outcome was assigned; " + note),
        EvalResult(name="episodes", metric="outcome accuracy", value=correct / n if n else None, n=n, notes="including 'unknown'; " + note),
        EvalResult(name="episodes", metric="not-an-episode rate", value=not_ep / len(rows) if rows else None, n=len(rows), notes=note),
    ]


def hazard_loo(db: Session, log=print) -> list[EvalResult]:
    """Leave-one-well-out: predict each documented well's (formation, hazard) outcomes from its offsets only.
    Sidetracks / wellbores of the same parent well are excluded from the offsets (not independent)."""
    reset()
    cx = ctx()
    c = cfg()["hazard"]
    wells = sorted(w for w in cx.documented if cx.wells[w].source == "sodir" and cx.tops.sequence(w))[: c["loo_max_wells"]]
    haz = list(taxonomy()["hazards"])
    sq_m = sq_b = 0.0
    sq_m_ok = sq_b_ok = 0.0
    n = n_ok = pos = 0
    for wid in wells:
        parent = cx.wells[wid].parent_well
        offs = [o for o in offsets_for_well(wid) if cx.wells[o["well_id"]].parent_well != parent]
        for f in set(cx.tops.sequence(wid)):
            for h in haz:
                p = hz.posterior(f, h, offs)
                y = 1 if (wid, f, h) in cx.ev_wf else 0
                base = p["prior"]["base_rate"]
                sq_m += (p["mean"] - y) ** 2
                sq_b += (base - y) ** 2
                n += 1
                pos += y
                if p["status"] == "ok":
                    sq_m_ok += (p["mean"] - y) ** 2
                    sq_b_ok += (base - y) ** 2
                    n_ok += 1
    note = (f"{len(wells)} Sodir wells × formations × {len(haz)} hazards; {pos} positive cases ({pos / max(n, 1):.2%}). "
            "Base rate is computed on all wells (includes the held-out well; small leak, stated). Lower is better.")
    log(f"hazard LOO: n={n} brier model={sq_m / n:.5f} base={sq_b / n:.5f}; ok-only n={n_ok}")
    return [
        EvalResult(name="hazard_loo", metric="Brier score (model)", value=sq_m / n if n else None, n=n, notes=note),
        EvalResult(name="hazard_loo", metric="Brier score (base rate)", value=sq_b / n if n else None, n=n, notes=note),
        EvalResult(name="hazard_loo", metric="Brier (model, n_eff ≥ min)", value=sq_m_ok / n_ok if n_ok else None, n=n_ok, notes="cases where the model reports a probability"),
        EvalResult(name="hazard_loo", metric="Brier (base, n_eff ≥ min)", value=sq_b_ok / n_ok if n_ok else None, n=n_ok, notes="same cases, base-rate prediction"),
    ]


def make_copilot_questions(db: Session, path) -> None:
    """25 answerable questions generated from templates over real trusted event lines (expected source =
    that line) + 5 out-of-scope questions that must be refused. Deterministic (seeded)."""
    cx = ctx()
    rng = random.Random(26121)
    evs = [e for lst in cx.events.values() for e in lst if cx.wells[e.well_id].source == "sodir" and e.md_m]
    rng.shuffle(evs)
    rows, seen = [], set()
    tpl = ["Was there {h} in well {w}?", "What {h} problems were recorded in {w}?", "Describe the {h} in well {w}."]
    for e in evs:
        if e.well_id in seen:
            continue
        seen.add(e.well_id)
        lbl = taxonomy()["hazards"][e.hazard]["label"].split(" /")[0].lower()
        rows.append({"question": rng.choice(tpl).format(h=lbl, w=cx.wells[e.well_id].canonical_name), "expected_source": e.source_ref, "should_refuse": 0})
        if len(rows) == 25:
            break
    for q in ["What is the unconfined compressive strength of the Hugin Formation?", "What was the Brent crude oil price in 2025?",
              "What losses were recorded in Assam well Naharkatiya-1?", "What is the friction angle of the Draupne shale?",
              "Who is the chairman of Oil India Limited?"]:
        rows.append({"question": q, "expected_source": "", "should_refuse": 1})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["question", "expected_source", "should_refuse"])
        w.writeheader()
        w.writerows(rows)


def copilot(db: Session) -> list[EvalResult]:
    from app.copilot.agent import answer
    p = EVAL_DIR / "copilot_questions.csv"
    if not p.exists():
        make_copilot_questions(db, p)
    rows = list(csv.DictReader(p.open()))
    cite_ok = cite_n = ref_ok = 0
    for r in rows:
        a = answer(db, r["question"])
        if r["should_refuse"] == "1":
            ref_ok += a["refused"]
        else:
            cite_n += 1
            cite_ok += (not a["refused"]) and any(s["ref"] == r["expected_source"] for s in a["sources"])
            ref_ok += not a["refused"]
    note = (f"{len(rows)} questions ({cite_n} answerable, generated from templates over real report lines; {len(rows) - cite_n} out-of-scope). "
            "Templated questions test routing and citation, not open-ended understanding.")
    return [
        EvalResult(name="copilot", metric="citation accuracy", value=cite_ok / cite_n if cite_n else None, n=cite_n, notes="expected report line cited; " + note),
        EvalResult(name="copilot", metric="refusal accuracy", value=ref_ok / len(rows) if rows else None, n=len(rows), notes="refused iff out of scope; " + note),
    ]


def run_all(db: Session, log=print):
    db.execute(delete(EvalResult))
    res = extraction(db) + episodes(db) + hazard_loo(db, log) + copilot(db)
    db.add_all(res)
    db.flush()
    for r in res:
        log(f"eval {r.name:11s} {r.metric:32s} {'—' if r.value is None else f'{r.value:.3f}'} (n={r.n})")
    return res
