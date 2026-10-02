""""Verify this number": for an accuracy figure on the Accuracy page, the labelled rows it was computed from, and the
figure RECOUNTED from those rows right now, side by side with the stored value.

A viewer can open every row's report line (source_ref) and check the label themselves. When a figure cannot be
broken into rows (AUC, Brier score), the reply says so and explains how it was computed, instead of showing nothing.
"""
from __future__ import annotations

import csv
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_DIR, EVAL_DIR
from app.db.models import Episode, EvalResult, Event


def _latest(pattern: str):
    files = sorted(EVAL_DIR.glob(pattern), key=lambda f: (len(f.stem), f.stem))
    return files[-1] if files else None


def _precision_check(pattern: str, what: str) -> dict:
    f = _latest(pattern)
    if not f:
        return {"rows": [], "recount": None}
    rows = list(csv.DictReader(f.open()))
    out = [{"ref": r["source_ref"], "text": r.get("evidence_start", ""), "system": r["hazard_extracted"].replace("_", " "),
            "truth": "real problem" if r["is_real_problem"] == "yes" else f"not a problem{(': ' + r['note']) if r.get('note') else ''}",
            "ok": r["is_real_problem"] == "yes", "labeller": r.get("labelled_by", "")} for r in rows]
    k = sum(r["ok"] for r in out)
    return {"file": f"data/eval/{f.name}", "rows": out, "recount": {"k": k, "n": len(out)},
            "columns": {"system": "Kupakosh extracted", "truth": "label (full line read)"},
            "how": f"Random sample of {what} that Kupakosh trusts. Each was labelled real problem / not a problem from its "
                   f"full report line. Precision = real problems ÷ sample."}


def _extraction(metric: str, db: Session) -> dict:
    p = EVAL_DIR / "events_gold.csv"
    if not p.exists():
        return {"rows": [], "recount": None}
    rows = list(csv.DictReader(p.open()))
    out, tp, fp, fn = [], 0, 0, 0
    for r in rows:
        true = {h for h in r["true_hazards"].split(";") if h}
        pred = {e.hazard for e in db.scalars(select(Event).where(Event.passage_id == int(r["passage_id"])))}
        a, b, c = len(pred & true), len(pred - true), len(true - pred)
        tp, fp, fn = tp + a, fp + b, fn + c
        out.append({"ref": r["source_ref"], "text": r["text"], "system": ", ".join(sorted(pred)).replace("_", " ") or "nothing",
                    "truth": ", ".join(sorted(true)).replace("_", " ") or "no problem", "ok": pred == true, "labeller": r.get("labeller", "")})
    if metric == "event recall":
        rc, how = {"k": tp, "n": tp + fn}, "Recall = hazards found ÷ hazards in the labels, over the same lines."
    elif metric == "event precision":
        rc, how = {"k": tp, "n": tp + fp}, "Precision = hazards found that are in the labels ÷ all hazards found."
    else:
        rc, how = None, "Depth check: extracted depth within the tolerance of the labelled depth, on lines that have one."
    return {"file": "data/eval/events_gold.csv", "rows": out, "recount": rc, "how": how + " Counted per hazard, so one line can count twice.",
            "columns": {"system": "Kupakosh extracted", "truth": "labelled hazards"}}


def _episodes(metric: str, db: Session) -> dict:
    tuning = "tuning set" in metric
    f = EVAL_DIR / "episodes_gold.csv" if tuning else _latest("episodes_fresh_r*.csv")
    if not f or not f.exists():
        return {"rows": [], "recount": None}
    by = {(ev.source_ref, ep.hazard): ep.outcome for ep, ev in db.execute(select(Episode, Event).join(Event, Event.id == Episode.event_id))}
    out, c, n, ko, kn, na = [], 0, 0, 0, 0, 0
    rows = list(csv.DictReader(f.open()))
    for r in rows:
        pred = by.get((r["event_source_ref"], r["hazard"]))
        if pred is None:
            continue
        if r["true_outcome"] == "n/a":
            na += 1
            out.append({"ref": r["event_source_ref"], "text": r["event_text"], "system": pred, "truth": "not a problem episode", "ok": None,
                        "labeller": r.get("labeller", "")})
            continue
        n += 1
        c += pred == r["true_outcome"]
        if pred != "unknown":
            kn += 1
            ko += pred == r["true_outcome"]
        out.append({"ref": r["event_source_ref"], "text": r["event_text"], "system": pred, "truth": r["true_outcome"],
                    "ok": pred == r["true_outcome"], "labeller": r.get("labeller", "")})
    rc = {"k": ko, "n": kn} if metric == "outcome precision" else {"k": na, "n": len(rows)} if metric == "not-an-episode rate" else {"k": c, "n": n}
    return {"file": f"data/eval/{f.name}", "rows": out, "recount": rc,
            "columns": {"system": "Kupakosh outcome", "truth": "labelled outcome"},
            "how": ("Each problem's outcome (resolved / partial / unresolved / worsened / unknown) against a label made from the "
                    "problem line and the lines after it. Accuracy counts 'unknown'; precision counts only episodes where Kupakosh "
                    "assigned an outcome. Rows marked 'not a problem episode' are excluded.")}


def _hindsight(metric: str) -> dict:
    p = DATA_DIR / "processed" / "hindsight_summary.json"
    if not p.exists():
        return {"rows": [], "recount": None}
    s = json.loads(p.read_text())
    wells = sorted(s["wells"], key=lambda w: -w["events"])
    out = [{"ref": None, "well_id": w["well_id"], "text": f"{w['name']} · {w['country']} · {w['n_offsets']} offset wells",
            "system": f"{w['forewarned']} forewarned, {w['alerts']} alerts", "truth": f"{w['events']} recorded problems",
            "ok": None, "labeller": ""} for w in wells if w["events"]]
    rc = None
    if metric.startswith("forewarned share"):
        rc = {"k": sum(w["forewarned"] for w in wells), "n": sum(w["events"] for w in wells)}
    how = ("Every documented well was replayed as if new, with a model trained only on other wells (grouped by wellbore family). "
           "The per-well rows add up to the forewarned share. ")
    if "AUC" in metric or "top 3" in metric or "layer flagged" in metric or "lift" in metric or "rate" in metric:
        how += ("This figure is computed over all (well, layer, hazard) cells together, not per well, so the per-well rows "
                "show the inputs (problems, alerts) rather than a recount. Open a well on the Hindsight page to see each alert "
                "and each problem with its report line.")
    return {"file": "data/processed/hindsight_summary.json", "rows": out, "recount": rc, "how": how,
            "columns": {"system": "Kupakosh (blind replay)", "truth": "the well's own reports"}}


def evidence(db: Session, name: str, metric: str) -> dict:
    stored = db.scalars(select(EvalResult).where(EvalResult.name == name, EvalResult.metric == metric)).first()
    base = {"name": name, "metric": metric, "stored": {"value": stored.value, "n": stored.n, "notes": stored.notes} if stored else None}
    if name == "volve_ddr":
        d = _precision_check("volve_ddr_events_check*.csv", "events from the Volve daily drilling reports")
    elif name == "nlog_reports":
        d = _precision_check("nlog_events_check_r*.csv", "events from the Dutch NLOG well reports")
    elif name == "extraction":
        d = _extraction(metric, db)
    elif name == "episodes":
        d = _episodes(metric, db)
    elif name in ("hindsight", "hindsight_by_source"):
        d = _hindsight(metric)
    elif name == "copilot":
        p = EVAL_DIR / "copilot_questions.csv"
        rows = list(csv.DictReader(p.open())) if p.exists() else []
        d = {"file": "data/eval/copilot_questions.csv", "recount": None,
             "rows": [{"ref": r["expected_source"] or None, "text": r["question"], "system": "—",
                       "truth": "must refuse" if r["should_refuse"] == "1" else "must cite this line", "ok": None, "labeller": ""} for r in rows],
             "columns": {"system": "", "truth": "expected"},
             "how": "Ask each question to the copilot; count answers citing the expected report line, and out-of-scope questions refused. "
                    "Re-run with `python -m app.eval` (the copilot is not re-asked from this page)."}
    else:
        d = {"rows": [], "recount": None, "how": "This figure has no row-level breakdown (for example a Brier score over every "
                                                   "well × layer × hazard case). See the notes for how it was computed."}
    rc = d.get("recount")
    if rc:
        rc["value"] = rc["k"] / rc["n"] if rc["n"] else None
        sv = base["stored"]["value"] if base["stored"] else None
        rc["matches_stored"] = sv is not None and rc["value"] is not None and abs(rc["value"] - sv) < 5e-4
    labellers = sorted({r.get("labeller") for r in d.get("rows", []) if r.get("labeller")})
    return {**base, **d, "labellers": labellers}
