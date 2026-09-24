"""Copilot (SPEC.md §9.11) — research-style answers built only from tool outputs.

This build has no LLM key, so the agent is deterministic ("extractive mode"):
  1. parse the question for wells, formations, hazards and intent
  2. call tools: search_evidence (BM25 keyword retrieval over every report line), get_wiki,
     nearby_wells, hazard_profile, ledger, mud_window
  3. compose the answer from tool outputs only; every sentence cites its source
  4. if no tool returns evidence -> "No evidence found in the records."
Never generates SQL; numbers come only from tool outputs.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import cfg, taxonomy
from app.db.models import Document, Passage, Well, WikiPage
from app.engines import hazard as hz
from app.engines import mudwindow as mw
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.ledger import ledger
from app.engines.offsets import offsets_for_well
from app.wiki.compiler import ACTION_LABEL

REFUSAL = "No evidence found in the records."
STOP = set("a an the of in on at to for and or is are was were be been what which who whom how why when where did do does "
           "any there this that these those with from by as it its me my we our you your can could should would will i "
           "tell show give list about well wells happened happen".split())
_TOK = re.compile(r"[a-zæøå0-9/]+(?:-[a-z0-9]+)*", re.I)


def tok(s: str) -> list[str]:
    return [t.lower() for t in _TOK.findall(s)]


@lru_cache(maxsize=1)
def _index():
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        rows = db.execute(select(Passage.id, Passage.text, Passage.document_id, Passage.locator, Passage.well_id)).all()
    docs = [tok(r[1]) for r in rows]
    return BM25Okapi(docs), rows, docs


@lru_cache(maxsize=1)
def _names():
    cx = ctx()
    wells = sorted(((w.canonical_name, w.id) for w in cx.wells.values() if w.id in cx.documented), key=lambda x: -len(x[0]))
    forms = {}
    for f in cx.penetrated:
        base = re.sub(r"\s+(FM|GP)$", "", f).lower()
        if len(base) >= 3 and base not in ("no formal name", "undefined", "undifferentiated"):
            forms.setdefault(base, f)
    return wells, forms


def parse(q: str) -> dict:
    wells, forms = _names()
    ql = q.lower()
    found_w = []
    for name, wid in wells:
        if re.search(r"(?<![\w/])" + re.escape(name.lower()) + r"(?![\w])", ql):
            found_w.append((name, wid))
            ql = ql.replace(name.lower(), " ")
    found_f = [f for base, f in forms.items() if re.search(r"\b" + re.escape(base) + r"\b", ql)]
    haz = []
    for k, v in taxonomy()["hazards"].items():
        if any(re.search(p, q, re.I) for p in v["include"]) or v["label"].lower() in ql or k.replace("_", " ") in ql:
            haz.append(k)
    syn = {"loss": "lost_circulation", "losses": "lost_circulation", "stuck": "stuck_pipe", "kick": "kick", "kicks": "kick",
           "torque": "torque_spike", "cement": "cementing_issue", "fishing": "fishing", "overpressure": "overpressure",
           "cavings": "wellbore_instability", "instability": "wellbore_instability", "tight": "stuck_pipe"}
    for t in tok(q):
        if t in syn and syn[t] not in haz:
            haz.append(syn[t])
    intent = []
    if re.search(r"\b(work(ed|s)?|fix|cure|mitigat|remed|resolv|what (was )?done|action|solution|how (to|did))", ql):
        intent.append("ledger")
    if re.search(r"\b(near|nearby|offset|around|within|radius|close)\b", ql):
        intent.append("nearby")
    if re.search(r"\b(mud weight|mud window|window|lot|fit|leak.?off|ppg|density)\b", ql):
        intent.append("mudwindow")
    if re.search(r"\b(probab|risk|chance|likel|expect|how often|rate)\b", ql):
        intent.append("hazard")
    return {"wells": found_w, "formations": found_f, "hazards": haz, "intent": intent}


def search_evidence(q: str, well_ids: set[int] | None = None, k: int | None = None) -> list[dict]:
    c = cfg()["copilot"]
    bm, rows, docs = _index()
    qt = [t for t in tok(q) if t not in STOP]
    if not qt:
        return []
    scores = bm.get_scores(qt)
    if well_ids:
        mask = np.array([r[4] in well_ids for r in rows])
        scores = np.where(mask, scores, 0)
    top = np.argsort(-scores)[: (k or c["top_k"]) * 3]
    out = []
    for i in top:
        if scores[i] <= 0:
            break
        overlap = len(set(qt) & set(docs[i])) / len(set(qt))
        if overlap < c["min_overlap"]:
            continue
        r = rows[i]
        out.append({"passage_id": r[0], "text": r[1], "source_ref": f"doc:{r[2]}#{r[3]}", "well_id": r[4], "score": round(float(scores[i]), 2),
                    "overlap": round(overlap, 2)})
        if len(out) >= (k or c["top_k"]):
            break
    return out


def answer(db: Session, question: str, context_well: int | None = None) -> dict:
    cx = ctx()
    P = parse(question)
    steps, paras, sources = [], [], []

    def cite(ref: str, label: str | None = None) -> str:
        if ref not in [s["ref"] for s in sources]:
            sources.append({"ref": ref, "label": label})
        return f"[{[s['ref'] for s in sources].index(ref) + 1}]"

    wells = P["wells"] or ([(cx.wells[context_well].canonical_name, context_well)] if context_well else [])
    well_ids = {w for _, w in wells}

    # nearby wells
    if "nearby" in P["intent"] and wells:
        name, wid = wells[0]
        offs = offsets_for_well(wid, documented_only=True)[:8]
        steps.append({"tool": "nearby_wells", "args": {"well": name}, "result": f"{len(offs)} documented offsets"})
        if offs:
            items = ", ".join(f"{o['name']} ({o['raw']['distance_m']:,} m, similarity {o['sim']:.2f})" for o in offs[:6])
            paras.append(f"Nearest documented wells to {name}: {items} {cite(f'query:offsets?well={name}', 'offset selection')}.")
            well_ids |= {o["well_id"] for o in offs}

    # hazard probability
    if "hazard" in P["intent"] and P["formations"] and P["hazards"] and wells:
        name, wid = wells[0]
        offs = offsets_for_well(wid)
        for f in P["formations"][:2]:
            for h in P["hazards"][:2]:
                p = hz.posterior(f, h, offs)
                steps.append({"tool": "hazard_profile", "args": {"well": name, "formation": f, "hazard": h}, "result": p["status"]})
                ref = cite(f"query:hazard?well={name}&formation={f}&hazard={h}", "hazard model")
                if p["status"] == "ok":
                    paras.append(f"Recorded-problem rate for {p['label'].lower()} in {pretty(f)} near {name}: {p['mean'] * 100:.0f}% "
                                 f"(80% range {p['ci'][0] * 100:.0f}–{p['ci'][1] * 100:.0f}%, effective evidence {p['n_eff']:.1f} wells) {ref}.")
                else:
                    paras.append(f"Insufficient evidence for {p['label'].lower()} in {pretty(f)} near {name}: effective evidence {p['n_eff']:.1f} wells, "
                                 f"below the minimum {cfg()['hazard']['min_neff']} {ref}.")

    # ledger
    if "ledger" in P["intent"] and P["hazards"]:
        for h in P["hazards"][:2]:
            f = P["formations"][0] if P["formations"] else None
            L = ledger(db, h, f, list(well_ids) if (well_ids and "nearby" in P["intent"]) else None)
            rows = [r for r in L["rows"] if r["n"] > 0][:3]
            steps.append({"tool": "ledger", "args": {"hazard": h, "formation": f}, "result": f"{len(rows)} actions with known outcome"})
            if rows:
                lbl = taxonomy()["hazards"][h]["label"].lower()
                bits = []
                for r in rows:
                    k = r["k"] if r["k"] % 1 else int(r["k"])
                    bits.append(f"{ACTION_LABEL.get(r['action'], r['action'])} worked in {k} of {r['n']}" + (" (anecdotal)" if r["anecdotal"] else "")
                                + (f", made worse {r['worsened']}" if r["worsened"] else ""))
                scope = f" in {pretty(f)}" if f else ""
                q = f"query:ledger?hazard={h}" + (f"&formation={f}" if f else "")
                paras.append(f"What worked against {lbl}{scope} (episodes with a stated outcome): " + "; ".join(bits) + f" {cite(q, 'mitigation ledger')}.")

    # mud window
    if "mudwindow" in P["intent"] and wells:
        name, wid = wells[0]
        ids = [o["well_id"] for o in offsets_for_well(wid)] + [wid]
        res = mw.window(db, ids, P["formations"][0] if P["formations"] else None)
        steps.append({"tool": "mud_window", "args": {"well": name}, "result": f"{len(res['formations'])} formations with evidence"})
        for r in res["formations"][:4]:
            lo = f"{r['lower_ppg']:.2f}" if r["lower_ppg"] else "no lower evidence"
            hi = f"{r['upper_ppg']:.2f}" if r["upper_ppg"] else "no upper evidence"
            paras.append(f"{r['label']}: lower bound {lo}, upper bound {hi} ppg ({r['status'].replace('_', ' ')}) {cite('query:mudwindow?well=' + name + '&formation=' + r['formation'], 'mud window')}.")

    # wiki
    wiki_hits = []
    for f in P["formations"][:2]:
        from app.wiki.compiler import fslug
        p = db.scalars(select(WikiPage).where(WikiPage.slug == f"formations/{fslug(f)}")).first()
        if p:
            wiki_hits.append(p)
    for name, _ in wells[:2]:
        from app.ingest.well_ids import slug as ws
        p = db.scalars(select(WikiPage).where(WikiPage.slug == f"wells/{ws(name)}")).first()
        if p:
            wiki_hits.append(p)
    if wiki_hits:
        steps.append({"tool": "get_wiki", "args": {"pages": [p.slug for p in wiki_hits]}, "result": f"{len(wiki_hits)} pages"})

    # evidence search (always)
    ev = search_evidence(question, well_ids or None)
    if not ev and well_ids:
        ev = search_evidence(question)
    steps.append({"tool": "search_evidence", "args": {"query": question, "wells": sorted(well_ids)}, "result": f"{len(ev)} passages"})
    for e in ev[:4]:
        wname = cx.wells[e["well_id"]].canonical_name if e["well_id"] in cx.wells else "?"
        paras.append(f"{wname}: “{e['text']}” {cite(e['source_ref'], wname)}")

    if not paras:
        return {"question": question, "refused": True, "answer": REFUSAL, "method": steps, "sources": [], "parsed": _jsonable(P),
                "mode": "extractive (no LLM configured)"}
    return {"question": question, "refused": False, "answer": "\n\n".join(paras), "method": steps, "sources": sources,
            "wiki": [{"slug": p.slug, "title": p.title, "status": p.status} for p in wiki_hits], "parsed": _jsonable(P),
            "mode": "extractive (no LLM configured)"}


def _jsonable(P):
    return {"wells": [n for n, _ in P["wells"]], "formations": P["formations"], "hazards": P["hazards"], "intent": P["intent"]}
