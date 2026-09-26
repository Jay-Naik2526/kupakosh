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
from app.db.models import Event, Passage, WikiPage
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
           "tell show give list about well wells happened happen worked work works against formation formations group problems "
           "problem recorded record near nearby offset offsets there any".split())
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
    return {"wells": found_w, "formations": found_f, "hazards": haz, "intent": intent, "basins": find_basins(q)}


@lru_cache(maxsize=1)
def _basin_names() -> list[tuple[str, int, str, int]]:
    """(match phrase, basin id, display name, document id) for Indian basins; longest phrases first."""
    from app.db.models import Basin
    from app.db.session import SessionLocal
    out = []
    with SessionLocal() as db:
        for b in db.scalars(select(Basin)):
            base = re.sub(r"(?i)\bbasin\b|-nec\b", "", b.name).strip().lower()
            phrases = {base, base.replace("-", " "), b.slug.replace("-", " ")}
            if "krishna" in base:
                phrases |= {"kg basin", "k-g basin"}
            for ph in phrases:
                if len(ph) >= 4:
                    out.append((ph, b.id, b.name, b.document_id))
    return sorted(out, key=lambda x: -len(x[0]))


def find_basins(q: str) -> list[tuple[int, str, int]]:
    ql = q.lower().replace("-", " ")
    found = []
    for ph, bid, name, did in _basin_names():
        if re.search(r"\b" + re.escape(ph.replace("-", " ")) + r"\b", ql) and bid not in [f[0] for f in found]:
            found.append((bid, name, did))
    return found


@lru_cache(maxsize=1)
def _dense_map():
    """Row position in the BM25 index -> row in the embedding matrix (-1 = not embedded)."""
    from app.search import embeddings
    ix = embeddings.index()
    if ix is None:
        return None
    pos = {int(p): i for i, p in enumerate(ix[0])}
    _, rows, _ = _index()
    return np.array([pos.get(r[0], -1) for r in rows], dtype=np.int64)


def _dense_scores(q: str) -> np.ndarray | None:
    """Cosine similarity of every indexed passage to the question, aligned to the BM25 rows (None = no embeddings)."""
    from app.search import embeddings
    m = _dense_map()
    if m is None:
        return None
    ids, vec = embeddings.index()
    c = cfg()["embeddings"]
    qv = embeddings.model().encode([c["query_prefix"] + q], normalize_embeddings=True)[0].astype(np.float32)
    s = vec @ qv
    return np.where(m >= 0, s[np.maximum(m, 0)], -1.0)


def retrieval_mode() -> str:
    return "hybrid (keyword BM25 + meaning, bge-small)" if _dense_map() is not None else "keyword (BM25)"


def search_evidence(q: str, well_ids: set[int] | None = None, k: int | None = None, doc_ids: set[int] | None = None,
                    min_overlap: float | None = None) -> list[dict]:
    """Hybrid retrieval: keyword (BM25) and meaning (embeddings) ranks fused by reciprocal rank.
    A passage is kept only if it shares enough of the question's words, or — found by meaning alone — is very similar."""
    c, ce = cfg()["copilot"], cfg()["embeddings"]
    bm, rows, docs = _index()
    qt = [t for t in tok(q) if t not in STOP]
    if not qt:
        return []
    mask = np.ones(len(rows), dtype=bool)
    if well_ids:
        mask &= np.array([r[4] in well_ids for r in rows])
    if doc_ids is not None:
        mask &= np.array([r[2] in doc_ids for r in rows])
    kw = np.where(mask, bm.get_scores(qt), 0)
    ncand = ce["candidates"]
    kw_top = [i for i in np.argsort(-kw)[:ncand] if kw[i] > 0]
    dense = _dense_scores(q)
    de_top = []
    if dense is not None:
        dm = np.where(mask, dense, -1.0)
        de_top = [i for i in np.argsort(-dm)[:ncand] if dm[i] > 0]
    fused: dict[int, float] = {}
    for rank_list in (kw_top, de_top):
        for r, i in enumerate(rank_list):
            fused[i] = fused.get(i, 0.0) + 1.0 / (ce["rrf_k"] + r + 1)
    kw_set, de_set = set(kw_top), set(de_top)
    need = min_overlap if min_overlap is not None else c["min_overlap"]
    out = []
    for i in sorted(fused, key=lambda i: -fused[i]):
        overlap = len(set(qt) & set(docs[i])) / len(set(qt))
        cos = float(dense[i]) if dense is not None else None
        if overlap < need and not (cos is not None and cos >= ce["min_cos"]):
            continue
        r = rows[i]
        how = "both" if i in kw_set and i in de_set else "keyword" if i in kw_set else "meaning"
        out.append({"passage_id": r[0], "text": r[1], "source_ref": f"doc:{r[2]}#{r[3]}", "well_id": r[4], "score": round(fused[i], 4),
                    "overlap": round(overlap, 2), "cos": round(cos, 3) if cos is not None else None, "retrieved_by": how})
        if len(out) >= (k or c["top_k"]):
            break
    return out


def well_events(db: Session, well_ids: set[int], hazards: list[str]) -> list[Event]:
    q = select(Event).where(Event.well_id.in_(well_ids))
    if hazards:
        q = q.where(Event.hazard.in_(hazards))
    return db.scalars(q.order_by(Event.well_id, Event.md_m)).all()


def answer(db: Session, question: str, context_well: int | None = None, country: str | None = None) -> dict:
    cx = ctx()
    from app.db.models import Document
    cdocs = set(db.scalars(select(Document.id).where(Document.country == country))) if country else None
    P = parse(question)
    steps, paras, sources = [], [], []
    ql = question.lower()
    bad = [t for t in cfg()["copilot"]["unsupported_terms"] if t in ql]
    if bad:
        steps.append({"tool": "scope_check", "args": {"terms": bad}, "result": "not in the records"})
        return {"question": question, "refused": True, "answer": REFUSAL + f" (Kupakosh does not hold data on: {', '.join(bad)}.)",
                "method": steps, "sources": [], "parsed": _jsonable(P), "mode": f"extractive (no LLM configured) · retrieval: {retrieval_mode()}"}

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
            if not rows and f:
                paras.append(f"No {taxonomy()['hazards'][h]['label'].lower()} episode with a stated outcome is recorded in {pretty(f)}; "
                             f"showing all formations instead {cite(f'query:ledger?hazard={h}&formation={f}', 'mitigation ledger')}.")
                f = None
                L = ledger(db, h, None)
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

    # Indian basins (NDR / DGH public summaries)
    if P["basins"]:
        from app.db.models import Basin, Well as W
        for bid, bname, did in P["basins"][:2]:
            b = db.get(Basin, bid)
            steps.append({"tool": "basin_facts", "args": {"basin": bname}, "result": "NDR summary"})
            bits = []
            if b.category:
                bits.append(f"category {b.category}")
            if b.area_text:
                bits.append(f"“{b.area_text}”")
            if b.exploratory_wells:
                bits.append(f"{int(b.exploratory_wells):,} exploratory wells stated")
            if bits:
                paras.append(f"{bname} (India, NDR/DGH summary): " + "; ".join(bits) + f" {cite(b.url, 'NDR basin page')}.")
            if re.search(r"\bwells?\b", question, re.I):
                ws = db.scalars(select(W).where(W.source == "ndr_india", W.fact_url == b.url)).all()
                if ws:
                    items = ", ".join(f"{w.aliases[0]}" + (f" ({w.td_md_m:,.0f} m)" if w.td_md_m else "") for w in ws[:15])
                    paras.append(f"Wells named in the {bname} summary: {items} {cite(b.url, 'NDR basin page')}.")
        qb = question
        for ph, _, _, _ in _basin_names():
            qb = re.sub(r"(?i)\b" + re.escape(ph) + r"\b", " ", qb.replace("-", " "))
        qb = re.sub(r"(?i)\bbasin\b|\bindia\b", " ", qb)
        bev = search_evidence(qb, doc_ids={did for _, _, did in P["basins"]}, min_overlap=0.34, k=4)
        steps.append({"tool": "search_evidence", "args": {"query": qb.strip(), "basins": [n for _, n, _ in P["basins"]]}, "result": f"{len(bev)} passages"})
        for e in bev:
            paras.append(f"“{e['text'][:500]}” {cite(e['source_ref'], _doc_title(db, e['source_ref']))}")

    # structured: recorded events for the named wells
    if P["wells"]:
        evs = well_events(db, {w for _, w in P["wells"]}, P["hazards"])
        steps.append({"tool": "well_events", "args": {"wells": [n for n, _ in P["wells"]], "hazards": P["hazards"]}, "result": f"{len(evs)} events"})
        for e in evs[:6]:
            wname = cx.wells[e.well_id].canonical_name
            where = f" at {e.md_m:,.0f} m" if e.md_m else ""
            fm = f" ({pretty(e.formation)})" if e.formation else ""
            rv = " — flagged for review" if e.needs_review else ""
            paras.append(f"{wname}{where}{fm}{rv}: “{e.evidence_span}” {cite(e.source_ref, wname)}")
        if not evs and P["hazards"]:
            paras.append(f"No {', '.join(taxonomy()['hazards'][h]['label'].lower() for h in P['hazards'])} record was extracted for "
                         f"{', '.join(n for n, _ in P['wells'])}; this means none was recorded, not that none occurred "
                         f"{cite('query:events?well=' + P['wells'][0][0], 'events table')}.")

    # evidence search (always)
    qwords = question
    for name, _ in P["wells"]:
        qwords = re.sub(re.escape(name), " ", qwords, flags=re.I)
    ev = search_evidence(qwords, well_ids or None, doc_ids=cdocs)
    if not ev and well_ids:
        ev = search_evidence(question, doc_ids=cdocs)
    args = {"query": question, "wells": sorted(well_ids)} | ({"country": country} if country else {})
    steps.append({"tool": "search_evidence", "args": args, "result": f"{len(ev)} passages"})
    shown = {s["ref"] for s in sources}
    for e in [e for e in ev if e["source_ref"] not in shown][: (2 if P["wells"] else 4)]:
        wname = cx.wells[e["well_id"]].canonical_name if e["well_id"] in cx.wells else _doc_title(db, e["source_ref"])
        paras.append(f"{wname}: “{e['text']}” {cite(e['source_ref'], wname)}")

    if not paras:
        return {"question": question, "refused": True, "answer": REFUSAL, "method": steps, "sources": [], "parsed": _jsonable(P),
                "mode": f"extractive (no LLM configured) · retrieval: {retrieval_mode()}"}
    return {"question": question, "refused": False, "answer": "\n\n".join(paras), "method": steps, "sources": sources,
            "wiki": [{"slug": p.slug, "title": p.title, "status": p.status} for p in wiki_hits], "parsed": _jsonable(P),
            "mode": f"extractive (no LLM configured) · retrieval: {retrieval_mode()}"}


def _jsonable(P):
    return {"wells": [n for n, _ in P["wells"]], "formations": P["formations"], "hazards": P["hazards"], "intent": P["intent"],
            "basins": [n for _, n, _ in P.get("basins", [])]}


def _doc_title(db: Session, ref: str) -> str:
    from app.db.models import Document
    try:
        d = db.get(Document, int(ref.split(":")[1].split("#")[0]))
        return d.title if d else "record"
    except (ValueError, IndexError):
        return "record"
