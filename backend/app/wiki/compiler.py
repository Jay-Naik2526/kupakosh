"""USP1: Well Wiki compiler (SPEC.md §9.10).

Pages are written ONLY from structured rows and verbatim quoted passages. Every sentence ends
with a citation marker [^sN]. A post-check rejects any sentence without a citation and any number
that is not present in its facts or in the cited source text. No LLM is used in this build
(no API key configured), so the prose is deliberately plain.

Reference kinds used in citations:
  doc:<id>#<locator>          a verbatim report line
  sodir:<table>:<npdid>#...   a row of a Sodir table
  query:<kind>?k=v&...        a reproducible database query (the UI shows the matching rows)
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import cfg, taxonomy
from app.db.models import AuditFlag, CasingString, Episode, Event, Passage, PressureTest, Well, WikiNoting, WikiPage
from app.engines.auditor import trust_for_refs
from app.engines.context import ctx, reset
from app.engines.formations import pretty
from app.engines.ledger import ledger
from app.ingest.well_ids import slug as well_slug
from app.wiki import gitstore

NUM = re.compile(r"(?<![\w^])(\d+(?:[.,]\d+)?)")
ACTION_LABEL = {
    "lcm_pill": "pumping LCM / a pill", "reduce_mw": "reducing mud weight", "increase_mw": "increasing mud weight",
    "reduce_flow": "reducing flow rate", "circulate_condition": "circulating and conditioning", "ream_backream": "reaming / back-reaming",
    "jar": "jarring", "spot_pill": "spotting a pill (e.g. pipe-lax / diesel)", "pump_out": "pumping out of hole",
    "cement_plug": "setting a cement plug", "squeeze": "a cement squeeze", "shut_in_kill": "shutting in and killing the well",
    "pooh": "pulling out of hole", "sidetrack": "sidetracking", "change_bha": "changing the BHA / bit",
    "fishing_run": "a fishing run", "cut_and_abandon": "cutting / backing off the string",
}


class CitationError(ValueError):
    pass


def fslug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("ø", "o").replace("å", "a").replace("æ", "ae")).strip("-")


class PageBuilder:
    def __init__(self):
        self.lines: list[str] = []
        self.refs: list[str] = []
        self.rejected: list[str] = []

    def h(self, title: str):
        self.lines += ["", f"## {title}", ""]

    def _cite(self, refs: list[str]) -> str:
        marks = []
        for r in refs:
            if r not in self.refs:
                self.refs.append(r)
            marks.append(f"[^s{self.refs.index(r) + 1}]")
        return "".join(marks)

    def s(self, text: str, refs: list[str], facts: list = (), source_texts: list[str] = (), bullet: bool = False):
        """Add one sentence. Rejected (and logged) if it has no citation or an unsupported number."""
        if not refs:
            self.rejected.append(f"no citation: {text}")
            return
        allowed = {_norm(x) for x in facts if x is not None}
        for st in source_texts:
            allowed |= {_norm(m) for m in NUM.findall(st or "")}
        bad = [n for n in NUM.findall(text) if _norm(n) not in allowed]
        if bad:
            self.rejected.append(f"unsupported number(s) {bad}: {text}")
            return
        self.lines.append(("- " if bullet else "") + text.rstrip() + " " + self._cite(refs))

    def quote(self, text: str, ref: str, who: str):
        t = text.strip().replace("\n", " ")
        self.s(f'> "{t}" — {who}', [ref], facts=[], source_texts=[t, who], bullet=False)

    def blank(self):
        self.lines.append("")

    def body(self) -> str:
        foot = [f"[^s{i + 1}]: {r}" for i, r in enumerate(self.refs)]
        return "\n".join(self.lines).strip() + "\n\n" + "\n".join(foot) + "\n"


def _norm(x) -> str:
    s = str(x).replace(",", "")
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else f"{f:.4g}"
    except ValueError:
        return s


def check_citations(body: str) -> list[str]:
    """Post-check on a finished page body: every content line must end with a citation marker."""
    bad = []
    for line in body.splitlines():
        t = line.strip()
        if not t or t.startswith("#") or t.startswith("[^s") or t.startswith("---"):
            continue
        if not re.search(r"\[\^s\d+\]\s*$", t):
            bad.append(t)
    return bad


def _q(kind: str, **kw) -> str:
    return f"query:{kind}?{urlencode({k: v for k, v in kw.items() if v is not None})}"


def _fmt(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}" if nd else f"{x:,.0f}"


# ------------------------------------------------------------------ page builders
def formation_page(db: Session, formation: str) -> tuple[str, str, PageBuilder]:
    cx = ctx()
    tax = taxonomy()
    label = pretty(formation)
    wells = cx.penetrated.get(formation, set())
    pb = PageBuilder()
    pb.h("Summary")
    n = len(wells)
    pb.s(f"{label} has a formation top recorded in {n} documented wells in this dataset (wells with a report or history text).",
         [_q("formation_top", formation=formation)], facts=[n])
    tops = [t.top_md_m for w in wells for t in cx.tops.tops(w) if t.formation == formation and t.top_md_m is not None]
    if tops:
        lo, hi = min(tops), max(tops)
        pb.s(f"Recorded tops range from {_fmt(lo)} m to {_fmt(hi)} m MD.", [_q("formation_top", formation=formation)], facts=[round(lo), round(hi)])

    pb.h("Known hazards")
    any_h = False
    for hz_key, hz in tax["hazards"].items():
        ws = [w for w in wells if (w, formation, hz_key) in cx.ev_wf]
        if not ws:
            continue
        any_h = True
        k = len(ws)
        pb.s(f"{hz['label']} was recorded in {k} of {n} documented wells that penetrated {label}.",
             [_q("events", hazard=hz_key, formation=formation)], facts=[k, n])
        for w in sorted(ws, key=lambda x: cx.wells[x].canonical_name)[:3]:
            e = cx.ev_wf[(w, formation, hz_key)][0]
            pb.quote(e.evidence_span, e.source_ref, cx.wells[w].canonical_name)
    if not any_h:
        pb.s(f"No trusted hazard record was extracted for {label}; this means none was recorded, not that none occurred.",
             [_q("events", formation=formation)], facts=[])

    pb.h("What worked")
    wrote = False
    for hz_key, hz in tax["hazards"].items():
        L = ledger(db, hz_key, formation)
        rows = [r for r in L["rows"] if r["n"] > 0]
        if not rows:
            continue
        wrote = True
        for r in rows[:3]:
            act = ACTION_LABEL.get(r["action"], r["action"])
            tag = " (anecdotal)" if r["anecdotal"] else ""
            pb.s(f"{hz['label']}: {act} was followed by resolution in {_fmt(r['k'], 1) if r['k'] % 1 else int(r['k'])} of {r['n']} episodes with a known outcome{tag}.",
                 [_q("ledger", hazard=hz_key, formation=formation, action=r["action"])], facts=[r["k"], r["n"]], bullet=True)
            if r["worsened"]:
                pb.s(f"In {r['worsened']} of those episodes the situation got worse.", [_q("episodes", hazard=hz_key, formation=formation, action=r["action"], outcome="worsened")],
                     facts=[r["worsened"]], bullet=True)
    if not wrote:
        pb.s("No episode with a recorded action and outcome was found for this formation.", [_q("episodes", formation=formation)], facts=[])

    pb.h("Casing & cement notes")
    pts = db.scalars(select(PressureTest).where(PressureTest.formation == formation)).all()
    if pts:
        v = sorted(p.emw_ppg for p in pts)
        pb.s(f"{len(pts)} leak-off / formation-integrity tests were taken at casing shoes set in {label}, ranging from {v[0]:.2f} to {v[-1]:.2f} ppg equivalent mud weight.",
             [_q("pressure_test", formation=formation)], facts=[len(pts), f"{v[0]:.2f}", f"{v[-1]:.2f}"])
    cs = db.scalars(select(CasingString).where(CasingString.formation == formation, CasingString.shoe_md_m.is_not(None))).all()
    if cs:
        pb.s(f"{len({c.well_id for c in cs})} wells have a casing shoe set in {label}.", [_q("casing", formation=formation)], facts=[len({c.well_id for c in cs})])
    cem = [e for (w, f, h), evs in cx.ev_wf.items() if f == formation and h == "cementing_issue" for e in evs]
    for e in cem[:2]:
        pb.quote(e.evidence_span, e.source_ref, cx.wells[e.well_id].canonical_name)
    if not pts and not cs:
        pb.s("No casing or leak-off record is linked to this formation.", [_q("casing", formation=formation)], facts=[])

    pb.h("Related wells")
    rel = sorted({w for (w, f, h) in cx.ev_wf if f == formation}, key=lambda x: cx.wells[x].canonical_name)[:12]
    for w in rel:
        nm = cx.wells[w].canonical_name
        k = sum(len(v) for (ww, f, h), v in cx.ev_wf.items() if ww == w and f == formation)
        pb.s(f"[[wells/{well_slug(nm)}]] {nm}: {k} trusted event record(s) in {label}.", [_q("events", well=nm, formation=formation)], facts=[k], source_texts=[nm], bullet=True)
    return f"formations/{fslug(formation)}", label, pb


def hazard_page(db: Session, hazard: str) -> tuple[str, str, PageBuilder]:
    cx = ctx()
    hz = taxonomy()["hazards"][hazard]
    pb = PageBuilder()
    evs = [e for lst in cx.events.values() for e in lst if e.hazard == hazard]
    wells = {e.well_id for e in evs}
    pb.h("Summary")
    pb.s(f"{hz['label']} has {len(evs)} trusted event records in {len(wells)} wells in this dataset.",
         [_q("events", hazard=hazard)], facts=[len(evs), len(wells)])
    by_f = Counter(e.formation for e in evs if e.formation)
    pb.h("Where it happens")
    for f, k in by_f.most_common(8):
        n = len(cx.penetrated.get(f, set()))
        wk = len({e.well_id for e in evs if e.formation == f})
        pb.s(f"[[formations/{fslug(f)}]] {pretty(f)}: recorded in {wk} of {n} documented wells that penetrated it.",
             [_q("events", hazard=hazard, formation=f)], facts=[wk, n], source_texts=[pretty(f)], bullet=True)
    pb.h("What worked")
    L = ledger(db, hazard)
    for r in [r for r in L["rows"] if r["n"] > 0][:6]:
        act = ACTION_LABEL.get(r["action"], r["action"])
        tag = " (anecdotal)" if r["anecdotal"] else ""
        k = _fmt(r["k"], 1) if r["k"] % 1 else int(r["k"])
        pb.s(f"{act}: resolved or partly resolved in {k} of {r['n']} episodes with a known outcome{tag}; made worse in {r['worsened']}.",
             [_q("ledger", hazard=hazard, action=r["action"])], facts=[r["k"], r["n"], r["worsened"]], bullet=True)
    pb.s(f"{L['n_episodes'] - L['n_known_outcome']} of {L['n_episodes']} episodes have no outcome stated in the source text and are excluded from the rates.",
         [_q("episodes", hazard=hazard, outcome="unknown")], facts=[L["n_episodes"] - L["n_known_outcome"], L["n_episodes"]])
    pb.h("Examples")
    for e in sorted(evs, key=lambda e: -e.confidence)[:4]:
        pb.quote(e.evidence_span, e.source_ref, cx.wells[e.well_id].canonical_name)
    return f"hazards/{hazard}", hz["label"], pb


def well_page(db: Session, well_id: int) -> tuple[str, str, PageBuilder]:
    cx = ctx()
    w = cx.wells[well_id]
    pb = PageBuilder()
    wref = w.fact_url or f"query:well?id={w.id}"
    pb.h("Summary")
    facts = [x for x in [w.td_md_m and round(w.td_md_m), w.spud_date and w.spud_date.year, w.water_depth_m and round(w.water_depth_m)] if x]
    parts = [f"{w.canonical_name} is a {(w.purpose or w.well_type or 'well').lower()} wellbore"]
    if w.field_name:
        parts.append(f"in {w.field_name.title() if w.source == 'sodir' else w.field_name}")
    if w.spud_date:
        parts.append(f"spudded in {w.spud_date.year}")
    if w.td_md_m:
        parts.append(f"with total depth {_fmt(w.td_md_m)} m MD")
    pb.s(" ".join(parts) + ".", [wref], facts=facts, source_texts=[w.canonical_name])
    forms = [t.formation for t in cx.tops.tops(well_id) if t.level == "FORMATION"] or [t.formation for t in cx.tops.tops(well_id)]
    if forms:
        pb.s("Formations penetrated (top-down): " + ", ".join(f"[[formations/{fslug(f)}]] {pretty(f)}" for f in forms[:14]) + ".",
             [_q("formation_top", well=w.canonical_name)], facts=[], source_texts=[" ".join(pretty(f) for f in forms), w.canonical_name])
    pb.h("Known hazards")
    evs = sorted(cx.events.get(well_id, []), key=lambda e: (e.md_m or 0))
    if not evs:
        pb.s("No trusted hazard record was extracted for this well.", [_q("events", well=w.canonical_name)], facts=[])
    for e in evs[:12]:
        where = f" at {_fmt(e.md_m)} m" if e.md_m else ""
        inf = f" in {pretty(e.formation)}" if e.formation else ""
        pb.s(f"{taxonomy()['hazards'][e.hazard]['label']}{where}{inf}.", [e.source_ref], facts=[round(e.md_m) if e.md_m else None],
             source_texts=[e.formation or ""], bullet=True)
        pb.quote(e.evidence_span, e.source_ref, w.canonical_name)
    pb.h("What worked")
    eps = db.scalars(select(Episode).where(Episode.well_id == well_id, Episode.outcome != "unknown")).all()
    if not eps:
        pb.s("No episode with a stated outcome was found for this well.", [_q("episodes", well=w.canonical_name)], facts=[])
    for ep in eps[:8]:
        acts = ", ".join(ACTION_LABEL.get(a, a) for a in ep.action_types) or "no recorded action"
        pb.s(f"{taxonomy()['hazards'][ep.hazard]['label']}: {acts} — outcome {ep.outcome}.", [ep.outcome_ref or _q("episodes", id=ep.id)], facts=[], bullet=True)
    pb.h("Casing & cement notes")
    seen = set()
    for c in db.scalars(select(CasingString).where(CasingString.well_id == well_id, CasingString.shoe_md_m.is_not(None)).order_by(CasingString.shoe_md_m)):
        k = (c.od_in, round(c.shoe_md_m))
        if k in seen or len(seen) >= 8:
            continue
        seen.add(k)
        od = f'{c.od_in:g}"' if c.od_in else "casing"
        pb.s(f"{od} {(c.casing_type or '').strip().lower()} shoe at {_fmt(c.shoe_md_m)} m" + (f" in {pretty(c.formation)}" if c.formation else "") + ".",
             [c.source_ref], facts=[c.od_in and f"{c.od_in:g}", round(c.shoe_md_m)], source_texts=[c.formation or "", c.casing_type or ""], bullet=True)
    for p in db.scalars(select(PressureTest).where(PressureTest.well_id == well_id).order_by(PressureTest.md_m)).all()[:8]:
        pb.s(f"{p.kind} {p.emw_ppg:.2f} ppg EMW at {_fmt(p.md_m or 0)} m.", [p.source_ref], facts=[f"{p.emw_ppg:.2f}", round(p.md_m or 0)], bullet=True)
    if not seen:
        pb.s("No casing record is available for this well.", [_q("casing", well=w.canonical_name)], facts=[])
    flags = db.scalars(select(AuditFlag).where(AuditFlag.well_id == well_id)).all()
    if flags:
        pb.h("Open questions (report conflicts)")
        for f in flags[:6]:
            pb.s(f"Rule {f.rule}: sources disagree by {f.delta}.", [f.ref_a, f.ref_b], facts=[], source_texts=[f.delta or "", f.rule], bullet=True)
    pb.h("Related wells")
    from app.engines.offsets import offsets_for_well
    for o in [o for o in offsets_for_well(well_id, documented_only=True)][:6]:
        pb.s(f"[[wells/{well_slug(o['name'])}]] {o['name']}: {_fmt(o['raw']['distance_m'])} m away, similarity {o['sim']:.2f}.",
             [_q("offsets", well=w.canonical_name)], facts=[o["raw"]["distance_m"], f"{o['sim']:.2f}"], source_texts=[o["name"]], bullet=True)
    return f"wells/{well_slug(w.canonical_name)}", w.canonical_name, pb


def basin_page(db: Session, basin_id: int) -> tuple[str, str, PageBuilder]:
    """Indian sedimentary basin — compiled only from the NDR/DGH public summary page (cited line by line)."""
    from app.db.models import Basin
    b = db.get(Basin, basin_id)
    pb = PageBuilder()
    ps = db.scalars(select(Passage).where(Passage.document_id == b.document_id).order_by(Passage.seq)).all()
    ref = lambda p: f"doc:{p.document_id}#{p.locator}"
    pb.h("Summary")
    facts = [p for p in ps if re.search(r"(?i)area|category|located|lies|extends|limited by|sediment|thickness", p.text) and not p.locator.startswith("table")][:5]
    for p in facts:
        pb.s(p.text, [ref(p)], source_texts=[p.text])
    if b.exploratory_wells:
        pb.s(f"The NDR summary states {int(b.exploratory_wells):,} exploratory wells for this basin.", [b.url], facts=[int(b.exploratory_wells)])
    pb.h("Stratigraphy and petroleum system")
    strat = [p for p in ps if re.search(r"(?i)formation|group|shale|sandstone|limestone|source rock|reservoir|cap rock|seal", p.text)][:10]
    for p in strat:
        pb.s(p.text if len(p.text) < 400 else p.text[:400] + "…", [ref(p)], source_texts=[p.text], bullet=True)
    pb.h("Drilling-relevant statements")
    hz = re.compile(r"(?i)high pressure|overpressur|abnormal pressure|loss|lost circulation|stuck|kick|blow ?out|instabil|cavings|H2S|gas show|drilling problem|hole problem")
    hits = [p for p in ps if hz.search(p.text)][:8]
    for p in hits:
        pb.s(p.text if len(p.text) < 400 else p.text[:400] + "…", [ref(p)], source_texts=[p.text], bullet=True)
    if not hits:
        pb.s("The public NDR summary for this basin contains no statement about drilling problems; well-level reports need NDR registration.",
             [b.url], facts=[])
    pb.h("Wells named in the summary")
    wells = db.scalars(select(Well).where(Well.source == "ndr_india", Well.fact_url == b.url)).all()
    for w in wells[:20]:
        d = f", drilled depth {w.td_md_m:,.0f} m" if w.td_md_m else ""
        o = f", operator {w.operator}" if w.operator else ""
        pb.s(f"{w.aliases[0]}{d}{o}.", [b.url], facts=[round(w.td_md_m) if w.td_md_m else None], source_texts=[w.aliases[0], w.operator or ""], bullet=True)
    if not wells:
        pb.s("No individual well is named in the public summary.", [b.url], facts=[])
    return f"basins/{b.slug}", f"{b.name} (India)", pb


# ------------------------------------------------------------------ compile + store
KIND_CODE = {"formations": ("formation", "FRM"), "hazards": ("hazard", "HAZ"), "wells": ("well", "WEL"), "basins": ("basin", "BSN")}


def compile_all(db: Session, scope: str = "all", log=print, limit_wells: int | None = None,
                only: list[tuple[str, object]] | None = None) -> dict:
    """scope = all | hazards | formations | wells | basins; `only` = explicit (kind, key) targets for an
    incremental recompile after new documents arrive (changed pages go back to draft for review)."""
    reset()
    cx = ctx()
    targets = list(only) if only is not None else []
    if only is not None:
        scope = "incremental"
    if scope in ("all", "hazards"):
        targets += [("hazard", h) for h in taxonomy()["hazards"]]
    if scope in ("all", "formations"):
        fs = sorted({f for (w, f, h) in cx.ev_wf})
        targets += [("formation", f) for f in fs]
    if scope in ("all", "wells"):
        ws = sorted({w for w in cx.events if cx.events[w]}, key=lambda w: cx.wells[w].canonical_name)
        forge = [w for w in cx.wells if cx.wells[w].source == "forge"]
        ws = sorted(set(ws[: limit_wells or len(ws)]) | set(forge))
        targets += [("well", w) for w in ws]
    if scope in ("all", "basins"):
        from app.db.models import Basin
        targets += [("basin", b.id) for b in db.scalars(select(Basin).order_by(Basin.name))]
    files, stats = {}, Counter()
    existing = {p.slug: p for p in db.scalars(select(WikiPage))}
    counters = Counter(p.ref_no.split("/")[2] for p in existing.values())
    pending_notes = []
    produced: dict[str, tuple[str, object]] = {}
    for kind, key in targets:
        slug, title, pb = {"hazard": hazard_page, "formation": formation_page, "well": well_page, "basin": basin_page}[kind](db, key)
        if slug in produced and produced[slug] != (kind, key):
            # two records can normalise to one slug (e.g. "Baghjan-5" and "Baghjan--5"): keep both pages, distinct
            slug = f"{slug}-{key}"
        produced[slug] = (kind, key)
        body = pb.body()
        bad = check_citations(body)
        if bad:
            raise CitationError(f"{slug}: uncited lines {bad[:2]}")
        stats["rejected_sentences"] += len(pb.rejected)
        for r in pb.rejected:
            log(f"wiki: rejected in {slug}: {r[:140]}")
        page = existing.get(slug)
        prev = gitstore.read(slug + ".md")
        prev_body = prev.split("\n---\n", 1)[1] if prev and "\n---\n" in prev else None
        if page and prev_body is not None and prev_body.strip() == body.strip():
            stats["unchanged"] += 1
            continue
        code = KIND_CODE[slug.split("/")[0]][1]
        if not page:
            counters[code] += 1
            page = WikiPage(slug=slug, kind=kind, title=title, ref_no=f"{cfg()['ui']['file_prefix']}/WIKI/{code}/{counters[code]:04d}", version=0, status="draft")
            db.add(page)
            db.flush()
        page.version += 1
        page.status = "draft"
        page.approved_by = page.approved_at = None
        page.trust = trust_for_refs(db, [r for r in pb.refs if not r.startswith("query:")])
        page.n_sources = len(pb.refs)
        fm = {"id": slug, "kind": kind, "ref_no": page.ref_no, "version": page.version, "title": title, "status": page.status,
              "trust": page.trust, "sources": pb.refs[:40], "compiled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        files[slug + ".md"] = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body
        pending_notes.append((page, len(pb.refs), page.version))
        stats[kind] += 1
    files["index.md"] = _index(db)
    sha = gitstore.write_and_commit(files, f"compile: {sum(stats[k] for k in ('hazard', 'formation', 'well'))} pages ({scope})")
    for page, nref, ver in pending_notes:
        page.git_commit = sha
        para = (db.query(WikiNoting).filter(WikiNoting.page_id == page.id).count()) + 1
        db.add(WikiNoting(page_id=page.id, para_no=para, author="System", role="Compiler",
                          note=f"Draft v{ver} compiled from {nref} sources. Awaiting review.", action="compile", git_commit=sha))
    db.flush()
    log(f"wiki: {dict(stats)} commit {sha[:8] if sha else None}")
    return dict(stats)


def _index(db: Session) -> str:
    lines = ["# Kupakosh Well Wiki — index", ""]
    for p in db.scalars(select(WikiPage).order_by(WikiPage.kind, WikiPage.title)):
        lines.append(f"- [[{p.slug}]] {p.title} — {p.ref_no} v{p.version} ({p.status})")
    return "\n".join(lines) + "\n"
