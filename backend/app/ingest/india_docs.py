"""More public Indian documents -> documents + citable passages (and named Indian wells for events).

Groups (folder under data/raw/india -> document kind):
  dgh_activity/  DGH 'India — Petroleum Exploration and Production Activities' 2005-06..2014-15  -> DGH_REPORT
  ipng/          MoPNG 'Indian Petroleum & Natural Gas Statistics'                              -> STATISTICS
  oil_annual/    Oil India Limited annual reports 2015-16..2025-26                               -> ANNUAL_REPORT
  cag/           CAG performance audits (hydrocarbon exploration, rig utilisation)               -> AUDIT_REPORT
  oisd/          OISD safety alerts (public, by id)                                               -> SAFETY_ALERT
  legal/         Baghjan-5 blowout: NGT / court records (Indian Kanoon)                           -> JUDGMENT
  papers/        open-access papers on Indian wells                                               -> PAPER
Page text is cached in data/processed/india_text.json (large PDFs are slow to parse).
Wells: only when a sentence names a well ("well Baghjan-5", "well No. X") is an Indian well row created
(no coordinates; field = source); events are then attached to it by the normal extraction pipeline.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

import pdfplumber
from sqlalchemy.orm import Session

from app.config import DATA_DIR, RAW_DIR
from app.db.models import Document, Passage, Well
from app.ingest.sodir import split_sentences

INDIA = RAW_DIR / "india"
GROUPS = {
    "dgh_activity": ("DGH_REPORT", "DGH — India Petroleum Exploration & Production Activities {stem}", "https://www.ndrdgh.gov.in/NDR/pdf/{name}"),
    "ipng": ("STATISTICS", "MoPNG — Indian Petroleum & Natural Gas Statistics ({stem})", "https://mopng.gov.in/files/TableManagements/{name}"),
    "oil_annual": ("ANNUAL_REPORT", "Oil India Limited — Annual Report ({stem})", "https://www.oil-india.com/files/financial_results_documents/{name}"),
    "ongc_annual": ("ANNUAL_REPORT", "ONGC — Annual Report ({stem})", None),
    "cag": ("AUDIT_REPORT", "CAG audit — {stem}", None),
    "oisd": ("SAFETY_ALERT", "OISD safety alert #{id}", "https://oisd.gov.in/Image/GetSafetyAlertAttachmentByID?safetyAlertID={id}"),
    "legal": ("JUDGMENT", "Court record — {stem}", "https://indiankanoon.org/doc/{id}/"),
    "papers": ("PAPER", "Paper — {stem}", None),
}
CAG_URLS = {"cag_42_2015_ch5": "https://cag.gov.in/uploads/download_audit_report/2015/Union_Commercial_Performace_Hydrocarbon_Exploration_42_2015_chap_5.pdf",
            "cag_39_2015_rigs": "https://cag.gov.in/webroot/uploads/download_audit_report/2015/Union_Commercial_Performance_Utilisation_Rigs_39_2015.pdf"}
PAPER_URLS = {"gji_upper_assam_pore_pressure": "https://academic.oup.com/gji/article/216/1/659/5144768",
              "aapg_kg_onshore_deviated_wells": "https://www.searchanddiscovery.com/abstracts/html/2018/australia.90324/abstracts/2018.Perth.Pore.50.html"}
ONGC_URLS = {"ar2023-24": "https://ongcindia.com/documents/77751/2660534/ar2023-24.pdf",
             "annual_report15-16": "http://www.ongcindia.com/wps/wcm/PDF/AnnualReport/annual_report15-16.pdf"}
LICENCE = {"ONGC": "ONGC public annual report", "DGH_REPORT": "Govt. of India publication (DGH)", "STATISTICS": "Govt. of India publication (MoPNG)",
           "ANNUAL_REPORT": "Oil India Limited public annual report", "AUDIT_REPORT": "Govt. of India publication (CAG)",
           "SAFETY_ALERT": "Govt. of India publication (OISD)", "JUDGMENT": "public court record", "PAPER": "journal article (cited)"}
EVENT_KINDS = {"DGH_REPORT", "AUDIT_REPORT", "SAFETY_ALERT", "JUDGMENT", "PAPER", "BASIN_REPORT"}

_WELL = re.compile(r"\b[Ww]ells?\s+(?:No\.?\s*|number\s+)?((?:[A-Z][A-Za-z]{2,}(?:[ -][A-Z][A-Za-z]{2,})?)[ -]?#?\s?\d{1,3}[A-Z]?)\b")
# "Baghjan 5 Oil Well", "Baghjan-5 well", "Baghjan Well No. 5"
_WELL2 = re.compile(r"\b([A-Z][a-z]{3,})[ -]#?(\d{1,3})\s+(?:[Oo]il\s+|[Gg]as\s+|[Ee]xploratory\s+)?[Ww]ell\b")
_WELL3 = re.compile(r"\b([A-Z][a-z]{3,})\s+[Ww]ell\s+(?:No\.?\s*|#\s*)(\d{1,3})\b")
_JUNK = re.compile(r"(?i)^(explored|unexplored|onland|offshore|services?|figure|fig|table|annexure|block|phase|page|section|para|chapter|schedule|note|total|year|round|well)\b")


def find_well_name(s: str) -> str | None:
    for rx in (_WELL2, _WELL3):
        m = rx.search(s)
        if m and not _JUNK.match(m.group(1)):
            return f"{m.group(1)}-{m.group(2)}"
    m = _WELL.search(s)
    if m and not _JUNK.match(m.group(1)):
        return m.group(1)
    return None


def _html_text(p: Path) -> list[str]:
    h = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r'<div class="judgments".*?</div>\s*</div>', h, re.S) or re.search(r"<article.*?</article>", h, re.S)
    body = m.group(0) if m else h
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return [t]


def _pages(p: Path, cache: dict) -> list[str]:
    key = str(p.relative_to(RAW_DIR))
    if key in cache:
        return cache[key]
    if p.suffix.lower() == ".html":
        pages = _html_text(p)
    else:
        with open(p, "rb") as fh:
            if fh.read(5) != b"%PDF-":
                return []
        try:
            with pdfplumber.open(p) as pdf:
                pages = [pg.extract_text() or "" for pg in pdf.pages]
        except Exception:  # noqa: BLE001
            return []
    cache[key] = pages
    return pages


def _paragraphs(page: str) -> list[str]:
    """PDF text lines -> paragraphs (join wrapped lines; split on blank lines or sentence-final lines)."""
    out, cur = [], []
    for line in page.split("\n"):
        s = line.strip()
        if not s:
            if cur:
                out.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
        if s.endswith((".", ":", ";")) and len(" ".join(cur)) > 200:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", x).strip() for x in out if len(x.strip()) >= 30]


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    cache_p = DATA_DIR / "processed" / "india_text.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    n0 = len(cache)
    wells: dict[str, Well] = {}
    for folder, (kind, title_t, url_t) in GROUPS.items():
        d = INDIA / folder
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() not in (".pdf", ".html"):
                continue
            pages = _pages(p, cache)
            if not pages or sum(len(x) for x in pages) < 200:
                stats["unreadable_or_empty"] += 1
                continue
            full = "\n".join(pages)
            if kind == "SAFETY_ALERT" and "SAFETY ALERT" not in full.upper():
                continue
            ident = re.findall(r"\d+", p.stem)[-1] if re.findall(r"\d+", p.stem) else p.stem
            title = title_t.format(stem=p.stem, id=ident, name=p.name)
            if kind == "SAFETY_ALERT":
                m = re.search(r"Title:\s*([^\n]+)", full)
                ref = re.search(r"OISD/SA/[\w/&-]+", full)
                title = f"OISD safety alert {ref.group(0) if ref else '#' + ident}: {m.group(1).strip()[:110] if m else ''}"
            url = (CAG_URLS.get(p.stem) if kind == "AUDIT_REPORT" else PAPER_URLS.get(p.stem) if kind == "PAPER"
                   else ONGC_URLS.get(p.stem) if folder == "ongc_annual"
                   else url_t.format(name=p.name, id=ident, stem=p.stem) if url_t else None)
            h = hashlib.sha256(full.encode()).hexdigest()
            if db.query(Document).filter(Document.sha256 == h).first():
                stats["duplicate"] += 1
                continue
            doc = Document(well_id=None, kind=kind, title=title, url=url, path=str(p.relative_to(RAW_DIR.parent)), pages=len(pages),
                           is_scanned=False, sha256=h, licence=LICENCE["ONGC"] if folder == "ongc_annual" else LICENCE[kind])
            db.add(doc)
            db.flush()
            seq = 0
            for pi, page in enumerate(pages, start=1):
                for qi, par in enumerate(_paragraphs(page), start=1):
                    sents = split_sentences(par) if kind in EVENT_KINDS else [par]
                    for si, s in enumerate(sents, start=1):
                        if len(s) < 25:
                            continue
                        seq += 1
                        loc = f"page {pi}, para {qi}" + (f".s{si}" if len(sents) > 1 else "")
                        wid = None
                        if kind in EVENT_KINDS:
                            nm = find_well_name(s)
                            if nm:
                                wid = _india_well(db, wells, nm, doc, stats).id
                        db.add(Passage(document_id=doc.id, well_id=wid, locator=loc, seq=seq, text=s[:2000]))
            stats[f"docs_{kind}"] += 1
            stats["passages"] += seq
            db.flush()
            # subject well: when one named well dominates a document (e.g. the Baghjan-5 judgments), sentences that
            # do not name any well are attached to it — stated in the event's source document, lower confidence applies
            if kind in EVENT_KINDS:
                from sqlalchemy import func, select
                top = db.execute(select(Passage.well_id, func.count()).where(Passage.document_id == doc.id, Passage.well_id.is_not(None))
                                 .group_by(Passage.well_id).order_by(func.count().desc())).all()
                if top and top[0][1] >= 3 and (len(top) == 1 or top[0][1] >= 3 * top[1][1]):
                    db.query(Passage).filter(Passage.document_id == doc.id, Passage.well_id.is_(None)).update({"well_id": top[0][0]})
                    stats["docs_with_subject_well"] += 1
    if len(cache) != n0:
        cache_p.write_text(json.dumps(cache))
    log(f"india_docs: {dict(stats)}")
    return dict(stats)


def _india_well(db: Session, wells: dict, raw: str, doc: Document, stats: Counter) -> Well:
    name = re.sub(r"\s*#\s*", "-", raw.strip())
    name = re.sub(r"\s+(?=\d)", "-", name)
    key = f"IN: {name}"
    if key in wells:
        return wells[key]
    w = db.query(Well).filter(Well.canonical_name == key).first()
    if not w:
        w = Well(canonical_name=key, aliases=[raw], field_name="India (named in public reports)", source="india_text",
                 lat=None, lon=None, position_source=None, fact_url=doc.url, purpose=f"named in: {doc.title[:120]}")
        db.add(w)
        db.flush()
        stats["india_wells_named"] += 1
    wells[key] = w
    return w
