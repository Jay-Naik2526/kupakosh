"""More public Indian sources -> documents + citable passages (+ named Indian wells / field centroids).

Everything here was found and verified reachable (no login, no registration, no CAPTCHA) on 2026-09-26.
See data/raw/india_more/REPORT.md for what was tried and what failed (eparlib.sansad.in unreachable from
this network; OISD safety-alert ids beyond #90 all return an "Attachment Not Found" placeholder PDF, i.e.
there is nothing published past the ~90 already in data/raw/india/oisd; link.springer.com blocks
automated fetches with a JS "Client Challenge").

Groups (folder under data/raw/india_more -> document kind):
  legal/       IndianKanoon NGT/High Court orders on the Baghjan-5 blowout, beyond the 2 already in
               data/raw/india/legal                                              -> JUDGMENT
  pib/         Press Information Bureau releases on the Baghjan blowout          -> INCIDENT_REPORT
  papers/      Open-access papers/conference abstracts naming Indian wells/fields -> PAPER
  wikipedia/   Wikipedia articles (CC BY-SA) on specific blowouts (event-extracted) and on named
               oil fields/basins (reference only, kind OTHER)                    -> INCIDENT_REPORT | OTHER

Field-centroid coordinates (Wikipedia/Wikidata) are stored on a Well row whose canonical_name is
prefixed "IN-FIELD:" and whose well_type is "field_centroid" and position_source says so — this is
NOT a real well location and must never be treated as one (see SPEC.md field-centroid rule).
"""
from __future__ import annotations

import hashlib
import html
import re
from collections import Counter
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import RAW_DIR
from app.db.models import Document, Passage, Well
from app.ingest.india_docs import find_well_name
from app.ingest.sodir import split_sentences
from app.ingest.units import ft_to_m

SOURCE = {
    "name": "india_more",
    "country": "India",
    "url": "see data/raw/india_more/MANIFEST.csv",
    "licence": "mixed public sources (see MANIFEST.csv)",
    "raw_dir": "india_more",
}

BASE = RAW_DIR / "india_more"
KANOON_URL = "https://indiankanoon.org/doc/{id}/"
KANOON_LICENCE = "public court/tribunal record (IndianKanoon, cited not redistributed)"

LEGAL_DOCS = {
    # sha-stable file -> (title, indiankanoon id)
    "indiankanoon_113010833.html": ("Gautam Uzir vs Union of India & Ors — Gauhati High Court, 4 Oct 2021 (Baghjan-5 compensation PIL)", "113010833"),
    "indiankanoon_118063652.html": ("Bonani Kakkar vs Oil India Limited — NGT, 19 Feb 2021 (Baghjan-5 blowout)", "118063652"),
    "indiankanoon_153149018.html": ("Mridu Paban Phukon vs Union of India — 20 Oct 2023 (Baghjan-5 blowout)", "153149018"),
    "indiankanoon_159573867.html": ("Wildlife and Environment Conservation Organisation vs Ministry of Petroleum & Natural Gas — NGT, 6 Aug 2020 (Baghjan-5 blowout)", "159573867"),
    "indiankanoon_172053402.html": ("Bonani Kakkar vs Oil India Limited — NGT, 8 Aug 2023 (Baghjan-5 blowout)", "172053402"),
    "indiankanoon_173426509.html": ("Bonani Kakkar vs Oil India Limited — NGT, 30 Nov 2023 (Baghjan-5 blowout)", "173426509"),
    "indiankanoon_38069735.html": ("Bimal Gogoi vs Ministry of Environment, Forest & Climate Change — 24 Jan 2022 (Baghjan-5 blowout)", "38069735"),
    "indiankanoon_65364785.html": ("Bonani Kakkar vs Oil India Limited — NGT, 6 Aug 2020 (Baghjan-5 blowout)", "65364785"),
    "indiankanoon_72658736.html": ("Bonani Kakkar vs Oil India Limited — NGT, 13 Dec 2024 (Baghjan-5 blowout)", "72658736"),
    "indiankanoon_81679506.html": ("Bonani Kakkar vs Oil India Limited — NGT, 30 Nov 2023 (Baghjan-5 blowout, order 2)", "81679506"),
    "indiankanoon_84290277.html": ("Bonani Kakkar vs Oil India Limited — NGT, 24 Jun 2020 (Baghjan-5 blowout)", "84290277"),
    "indiankanoon_84394927.html": ("Wildlife and Environment Conservation Organisation vs Ministry of Petroleum & Natural Gas — NGT, 24 Jun 2020 (Baghjan-5 blowout)", "84394927"),
}

PIB_DOCS = {
    "pib_1630694.html": ("PIB — Statement on the Blowout in Gas Well of Oil India Limited at Baghjan, Tinsukia District, Assam", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1630694"),
    "pib_1632427.html": ("PIB — PM reviews situation of Oil Well Blow Out and fire in Assam (Baghjan)", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1632427"),
}
PIB_LICENCE = "Government of India public web content (PIB) — cited, not redistributed"

PAPER_DOCS = {
    # file -> (title, url, licence, event-extract?)
    "nature_baghjan.html": ("Seismic monitoring of the 2020 Baghjan oil-well blowout incident in Assam, India — Scientific Reports (2024)",
                             "https://www.nature.com/articles/s41598-024-74428-y", "CC BY 4.0 (Scientific Reports, open access)", True),
    "spg_p046.pdf": ("Predrill wellbore stability analysis using rock physical parameters for a deepwater high-angle well: a case study (Mondal, Karthikeyan & Patel) — SPG India 10th Biennial",
                      "https://www.spgindia.org/10_biennial_form/P046.pdf", "SPG India conference paper (public PDF, cited not redistributed)", True),
    "spg_p209.pdf": ("Reservoir Characterization Case Study, Cambay Basin, India (Chatterjee et al.) — SPG India 10th Biennial",
                      "https://spgindia.org/10_biennial_form/P209.pdf", "SPG India conference paper (public PDF, cited not redistributed)", False),
    "ndr_02.pdf": ("Prediction of Facies & Reservoir Properties in Carbonate Reservoir through Geo-body Modelling: Mumbai Offshore Case Study (DGH, EAGE workshop)",
                    "https://www.ndrdgh.gov.in/NDR/pdf/02.pdf", "Government of India publication (DGH/NDR)", False),
    "ndr_04.pdf": ("Geo-Body and Geostatistical Modelling of Carbonate Reservoir Facies Architecture and Characterization (Gorain, DGH) — Intl. J. Petroleum Technology 2023",
                    "https://www.ndrdgh.gov.in/NDR/pdf/04.pdf", "DGH-authored article, published by Avanti Publishers (cited not redistributed)", False),
}

# Wikipedia: incident articles (event-extracted) vs field/basin reference articles (OTHER, not extracted)
WIKI_INCIDENTS = {
    "wiki_Baghjan.html": "Wikipedia — Baghjan (Baghjan oilfield / 2020 blowout)",
    "wiki_Pasarlapudi_blowout.html": "Wikipedia — Pasarlapudi blowout (ONGC, Krishna-Godavari basin, 1995)",
}
WIKI_REFERENCE = {
    "wiki_Digboi_oil_field.html": "Wikipedia — Digboi oil field",
    "wiki_Naharkatiya_oil_field.html": "Wikipedia — Naharkatiya oil field",
    "wiki_Moran,_Assam.html": "Wikipedia — Moran, Assam (oilfield town)",
    "wiki_Lakwa.html": "Wikipedia — Lakwa (oilfield)",
    "wiki_Bombay_High_Field.html": "Wikipedia — Bombay High Field",
    "wiki_Ankleshwar.html": "Wikipedia — Ankleshwar (oilfield town)",
    "wiki_Kalol,_Gujarat.html": "Wikipedia — Kalol, Gujarat (oilfield town)",
    "wiki_Cambay_Basin.html": "Wikipedia — Cambay Basin",
    "wiki_Krishna_Godavari_Basin.html": "Wikipedia — Krishna Godavari Basin",
    "wiki_Assam-Arakan_Basin.html": "Wikipedia — Assam-Arakan Basin",
    "wiki_Barmer,_Rajasthan.html": "Wikipedia — Barmer, Rajasthan (Mangala/Thar Desert fields)",
    "wiki_Mangala_oil_field.html": "Wikipedia — Mangala oil field",
}
WIKI_LICENCE = "Wikipedia (CC BY-SA 4.0) — cited, not redistributed"
WIKI_URL = "https://en.wikipedia.org/wiki/{name}"

# field-centroid coordinates found via Wikipedia infobox / Wikidata P625 (never a real well location)
FIELD_CENTROIDS = [
    # canonical well-row name, field_name, lat, lon, position_source
    ("IN-FIELD: Baghjan Oilfield", "Baghjan Oilfield (Assam)", 27.6002, 95.4018, "field centroid (Wikipedia infobox)"),
    ("IN-FIELD: Mangala Oilfield", "Mangala Oilfield (Barmer, Rajasthan)", 25.9586495, 71.5095209, "field centroid (Wikipedia infobox)"),
    ("IN-FIELD: Digboi Oilfield", "Digboi Oilfield (Assam)", 27.38, 95.63, "field centroid (Wikidata Q1267577, Digboi town)"),
    ("IN-FIELD: Ankleshwar Oilfield", "Ankleshwar Oilfield (Gujarat)", 21.6, 73.0, "field centroid (Wikidata Q588924, Ankleshwar town)"),
]

EVENT_KINDS = {"INCIDENT_REPORT", "JUDGMENT", "PAPER"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _wiki_text(p: Path) -> str:
    h = p.read_text(encoding="utf-8", errors="ignore")
    i = h.find('id="mw-content-text"')
    if i < 0:
        return ""
    body = h[i:]
    for marker in ('id="catlinks"', 'class="printfooter"'):
        j = body.find(marker)
        if j > 0:
            body = body[:j]
    body = re.sub(r"<style.*?</style>|<script.*?</script>|<table[^>]*class=\"[^\"]*infobox[^\"]*\".*?</table>", "", body, flags=re.S)
    body = re.sub(r"<sup[^>]*class=\"reference\".*?</sup>", "", body, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    t = re.sub(r"\[edit\]", "", t)
    return t


def _kanoon_text(p: Path) -> str:
    h = p.read_text(encoding="utf-8", errors="ignore")
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    start = h.find("Document Options")
    body = h[start:] if start > 0 else h
    end = body.find("Related user Queries")
    if end > 0:
        body = body[:end]
    t = html.unescape(re.sub(r"<[^>]+>", "\n", body))
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _html_page_text(p: Path) -> str:
    h = p.read_text(encoding="utf-8", errors="ignore")
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", h))
    return t


def _pdf_pages(p: Path) -> list[str]:
    import pdfplumber
    try:
        with pdfplumber.open(p) as pdf:
            return [pg.extract_text() or "" for pg in pdf.pages]
    except Exception:  # noqa: BLE001
        return []


def _paragraphs(text: str) -> list[str]:
    out, cur = [], []
    for line in text.split("\n"):
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
    return [_clean(x) for x in out if len(x.strip()) >= 30]


def _add_doc(db: Session, stats: Counter, kind: str, title: str, url: str | None, licence: str, path: Path, full_text: str,
             pages: int, event_extract: bool, wells: dict[str, Well]) -> Document | None:
    if len(full_text.strip()) < 200:
        stats["unreadable_or_empty"] += 1
        return None
    h = hashlib.sha256(full_text.encode("utf-8", "ignore")).hexdigest()
    if db.query(Document).filter(Document.sha256 == h).first():
        stats["duplicate"] += 1
        return None
    doc = Document(well_id=None, kind=kind, title=title, url=url, path=str(path.relative_to(RAW_DIR.parent)),
                   pages=pages, is_scanned=False, sha256=h, licence=licence)
    db.add(doc)
    db.flush()
    seq = 0
    for pi, par in enumerate(_paragraphs(full_text), start=1):
        sents = split_sentences(par) if event_extract else [par]
        for si, s in enumerate(sents, start=1):
            if len(s) < 25:
                continue
            seq += 1
            loc = f"para {pi}" + (f".s{si}" if len(sents) > 1 else "")
            wid = None
            if event_extract:
                nm = find_well_name(s)
                if nm:
                    wid = _india_well(db, wells, nm, doc, stats).id
            db.add(Passage(document_id=doc.id, well_id=wid, locator=loc, seq=seq, text=s[:2000]))
    stats[f"docs_{kind}"] += 1
    stats["passages"] += seq
    db.flush()
    if event_extract and seq:
        from sqlalchemy import func, select
        top = db.execute(select(Passage.well_id, func.count()).where(Passage.document_id == doc.id, Passage.well_id.is_not(None))
                         .group_by(Passage.well_id).order_by(func.count().desc())).all()
        if top and top[0][1] >= 2 and (len(top) == 1 or top[0][1] >= 2 * top[1][1]):
            db.query(Passage).filter(Passage.document_id == doc.id, Passage.well_id.is_(None)).update({"well_id": top[0][0]})
            stats["docs_with_subject_well"] += 1
    return doc


def _india_well(db: Session, wells: dict, raw: str, doc: Document, stats: Counter) -> Well:
    name = re.sub(r"\s*#\s*", "-", raw.strip())
    name = re.sub(r"\s+(?=\d)", "-", name)
    key = f"IN: {name}"
    if key in wells:
        return wells[key]
    w = db.query(Well).filter(Well.canonical_name == key).first()
    if not w:
        w = Well(canonical_name=key, aliases=[raw], field_name="India (named in public reports)", country="India", source="india_more",
                 lat=None, lon=None, position_source=None, fact_url=doc.url, purpose=f"named in: {doc.title[:120]}")
        db.add(w)
        db.flush()
        stats["india_wells_named"] += 1
    wells[key] = w
    return w


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    wells: dict[str, Well] = {}

    # 1. Legal (IndianKanoon) — Baghjan-5 blowout NGT / court orders
    legal_dir = BASE / "legal"
    for fname, (title, kid) in LEGAL_DOCS.items():
        p = legal_dir / fname
        if not p.exists():
            continue
        txt = _kanoon_text(p)
        _add_doc(db, stats, "JUDGMENT", title, KANOON_URL.format(id=kid), KANOON_LICENCE, p, txt, pages=1, event_extract=True, wells=wells)

    # 2. PIB press releases
    pib_dir = BASE / "pib"
    for fname, (title, url) in PIB_DOCS.items():
        p = pib_dir / fname
        if not p.exists():
            continue
        txt = _html_page_text(p)
        _add_doc(db, stats, "INCIDENT_REPORT", title, url, PIB_LICENCE, p, txt, pages=1, event_extract=True, wells=wells)

    # 3. Papers (open-access, DGH, SPG India)
    papers_dir = BASE / "papers"
    for fname, (title, url, licence, event_extract) in PAPER_DOCS.items():
        p = papers_dir / fname
        if not p.exists():
            continue
        if p.suffix.lower() == ".pdf":
            pages = _pdf_pages(p)
            txt = "\n".join(pages)
            npages = len(pages)
        else:
            txt = _html_page_text(p)
            npages = 1
        _add_doc(db, stats, "PAPER", title, url, licence, p, txt, pages=npages, event_extract=event_extract, wells=wells)

    # 4. Wikipedia — incidents (event-extracted)
    wiki_dir = BASE / "wikipedia"
    for fname, title in WIKI_INCIDENTS.items():
        p = wiki_dir / fname
        if not p.exists():
            continue
        page_name = fname[len("wiki_"):-len(".html")]
        url = WIKI_URL.format(name=page_name)
        txt = _wiki_text(p)
        _add_doc(db, stats, "INCIDENT_REPORT", title, url, WIKI_LICENCE, p, txt, pages=1, event_extract=True, wells=wells)

    # 5. Wikipedia — field/basin reference articles (not event-extracted; OTHER)
    for fname, title in WIKI_REFERENCE.items():
        p = wiki_dir / fname
        if not p.exists():
            continue
        page_name = fname[len("wiki_"):-len(".html")]
        url = WIKI_URL.format(name=page_name)
        txt = _wiki_text(p)
        _add_doc(db, stats, "OTHER", title, url, WIKI_LICENCE, p, txt, pages=1, event_extract=False, wells=wells)

    # 6. Field-centroid coordinates (never a real well location — see SPEC.md)
    for name, field_name, lat, lon, pos_src in FIELD_CENTROIDS:
        if db.query(Well).filter(Well.canonical_name == name).first():
            continue
        db.add(Well(canonical_name=name, aliases=[], field_name=field_name, country="India", lat=lat, lon=lon,
                     well_type="field_centroid", position_source=pos_src, source="india_more",
                     purpose="Field centroid coordinate only (Wikipedia/Wikidata) — NOT a surveyed well location."))
        stats["field_centroids"] += 1
    db.flush()

    log(f"india_more: {dict(stats)}")
    return dict(stats)
