"""V3 USP: the Upper Assam column — Oil India's home geology in the words of public DGH/NDR records,
joined to measured drilling-problem evidence from analogue rock abroad.

Why: Oil India drills the Upper Assam shelf (Girujan, Tipam, Barail, Kopili, Sylhet, Langpar ...).
There is no public well-level drilling record for those wells, so this module never invents one.
Instead, for each formation it
  1. finds every loaded sentence that names it (NDR basin summary, DGH activity reports),
  2. reads rock type, geological age, role (reservoir / source rock / cap rock) and depth mentions
     only from those sentences, each fact quoted with its source_ref,
  3. asks the analog engine (app.engines.analogs) what was recorded in public wells abroad drilled
     through the same rock type: Bayesian problem rates with an 80 % range and evidence count, plus
     the fixes that worked there.
Rules and names live in config/assam.yaml. Every response carries the caveat from that file.
"""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

import yaml
from sqlalchemy import or_, select

from app.config import CONFIG_DIR
from app.db.models import Document, Passage
from app.db.session import SessionLocal
from app.engines.analogs import acfg as analogs_cfg
from app.engines.analogs import find_analogs


@lru_cache
def scfg() -> dict:
    return yaml.safe_load((CONFIG_DIR / "assam.yaml").read_text())


def _name_re(names: list[str]) -> re.Pattern:
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.I)


def _kw_re(kw: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(kw) + r"(?:s|es)?\b", re.I)  # "Disang shales" counts as shale


def _sentences(db) -> list[tuple[str, str, str]]:
    """(source_ref, text, document title) for every passage in a document that is about Assam or names one of
    the configured formations."""
    c = scfg()
    all_names = [n for f in c["formations"] for n in f["names"]]
    title_q = [Document.title.ilike(f"%{h}%") for h in c["doc_title_hints"]]
    name_q = [Passage.text.ilike(f"%{n}%") for n in all_names]
    doc_ids = set(db.scalars(select(Document.id).where(or_(*title_q))))
    doc_ids |= set(db.scalars(select(Passage.document_id).where(or_(*name_q)).distinct()))
    rows = db.execute(select(Passage.document_id, Passage.locator, Passage.text, Document.title)
                      .join(Document, Document.id == Passage.document_id)
                      .where(Passage.document_id.in_(doc_ids))).all()
    return [(f"doc:{d}#{loc}", t, title) for d, loc, t, title in rows if t]


def _lithology(hits: list[tuple[str, str, str]], name_re: re.Pattern, other_re: re.Pattern) -> dict | None:
    """Rock type from lithology words written right after the formation's name, e.g. 'Tipam Sandstone',
    'Girujan Clay', 'Kopili Formation, consisting of shales'."""
    c = scfg()
    kw = {k: list(v) + list(c.get("extra_keywords", {}).get(k, [])) for k, v in analogs_cfg()["keywords"].items()}
    counts: Counter = Counter()
    first: dict[str, tuple[str, str]] = {}
    for ref, text, _ in hits:
        for m in name_re.finditer(text):
            window = text[m.end(): m.end() + c["lithology_window_chars"]]
            nxt = other_re.search(window)  # stop at the next unit's name ("Kopili ... Barail Coal-Shale")
            if nxt:
                window = window[: nxt.start()]
            for cls, words in kw.items():
                if any(_kw_re(w).search(window) for w in words):
                    counts[cls] += 1
                    first.setdefault(cls, (ref, text))
    if not counts:
        return None
    (top, n1), *rest = counts.most_common()
    mixed = bool(rest) and rest[0][1] >= c["mixed_ratio"] * n1
    ref, text = first[top]
    return {"class": "mixed" if mixed else top, "counts": dict(counts), "source_ref": ref, "text": text}


def _age(hits: list[tuple[str, str, str]], name_re: re.Pattern) -> dict | None:
    c = scfg()
    pat = re.compile(c["age_pattern"], re.I)
    best = None
    for ref, text, _ in hits:
        for m in name_re.finditer(text):
            for a in pat.finditer(text):
                gap = a.start() - m.end() if a.start() >= m.end() else m.start() - a.end()
                if 0 <= gap <= c["age_window_chars"] and (best is None or gap < best[0]):
                    best = (gap, a.group(0).strip(), ref, text)
    if not best:
        return None
    return {"value": best[1], "source_ref": best[2], "text": best[3]}


def _roles(hits: list[tuple[str, str, str]]) -> list[dict]:
    out = []
    for role, phrases in scfg()["roles"].items():
        for ref, text, _ in hits:
            tl = text.lower()
            if any(p in tl for p in phrases):
                out.append({"role": role, "source_ref": ref, "text": text})
                break
    return out


def _depth_mentions(hits: list[tuple[str, str, str]], name_re: re.Pattern) -> list[dict]:
    pat = re.compile(scfg()["depth_pattern"])
    out = []
    for ref, text, _ in hits:
        for m in name_re.finditer(text):
            before = text[max(0, m.start() - 30): m.start()]
            d = list(pat.finditer(before))
            if d and int(d[-1].group(1)) not in {o["depth_m"] for o in out}:
                out.append({"depth_m": int(d[-1].group(1)), "source_ref": ref, "text": text})
    return out


def _analog_summary(cls: str | None) -> dict | None:
    if not cls:
        return None
    c = scfg()
    lo, hi = c["analog_band_m"]
    r = find_analogs(cls, lo, hi)
    if "error" in r:
        return None
    hz = [h for h in r["hazards"] if h["status"] == "ok" and h["n_with_event"] > 0]
    hz.sort(key=lambda h: -h["mean"])
    insufficient = [h["label"] for h in r["hazards"] if h["status"] != "ok"]
    documented = sum(x["n_wells_documented"] for x in r["by_country"])
    fixes = [{"action": f["action"], "label": f.get("label") or f["action"], "n": f["n"], "k": f["k"],
              "rate": f.get("rate"), "lb": f.get("lb"), "worsened": f.get("worsened", 0), "anecdotal": f.get("anecdotal")}
             for f in r["fixes"] if f.get("n", 0) > 0][: c["max_fixes"]]
    return {"lithology": cls, "band_m": [lo, hi], "n_intervals": r["n_intervals"], "n_wells": r["n_wells"],
            "n_wells_documented": documented,
            "countries": [x["country"] for x in r["by_country"][:5]],
            "hazards": [{"hazard": h["hazard"], "label": h["label"], "mean": h["mean"], "ci": h["ci"], "n_eff": h["n_eff"],
                         "n_wells": h["n_wells"], "n_with_event": h["n_with_event"], "examples": h.get("examples", [])[:2]}
                        for h in hz[: c["max_hazards"]]],
            "insufficient": insufficient, "fixes": fixes}


@lru_cache(maxsize=1)
def column() -> dict:
    c = scfg()
    with SessionLocal() as db:
        sentences = _sentences(db)
    rows = []
    for f in c["formations"]:
        name_re = _name_re(f["names"])
        other_re = _name_re([n for g in c["formations"] if g["key"] != f["key"] for n in g["names"]])
        hits = [s for s in sentences if name_re.search(s[1])]
        lith = _lithology(hits, name_re, other_re)
        quotes, seen = [], set()
        for ref, text, title in hits:  # prefer sentences that say what the rock is or does
            if ref in seen:
                continue
            seen.add(ref)
            quotes.append({"source_ref": ref, "text": text, "document": title})
        quotes.sort(key=lambda q: (not any(p in q["text"].lower() for ps in c["roles"].values() for p in ps), len(q["text"]) > 260))
        rows.append({
            "key": f["key"], "label": f["label"], "names": f["names"],
            "n_sentences": len(hits), "n_documents": len({h[0].split("#")[0] for h in hits}),
            "in_records": bool(hits),
            "lithology": lith, "age": _age(hits, name_re), "roles": _roles(hits),
            "depth_mentions": _depth_mentions(hits, name_re)[:3],
            "quotes": quotes[: c["max_quotes"]],
            "analogs": _analog_summary(lith["class"] if lith else None),
        })
    return {"formations": rows, "caveat": c["caveat"], "n_sentences_searched": len(sentences)}


def reset() -> None:
    column.cache_clear()
    scfg.cache_clear()
