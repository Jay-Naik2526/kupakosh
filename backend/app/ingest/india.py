"""Public Indian sources -> documents, passages, basins, listed wells.

Sources (all public web pages / PDFs of the Government of India, downloaded by scripts/download_india.sh):
  * NDR (National Data Repository, DGH) basin summary pages — 23 sedimentary basins
  * NDR technical papers (incl. 'Analyzing average rig time and ease of drilling in Indian sedimentary basins')
  * NDR data policy / geoscientific data policy PDFs
What this is NOT: well-level daily drilling reports. Those sit behind NDR registration (see docs/INDIA_DATA.md).
Every paragraph and table row becomes a citable passage (locator 'para N' / 'table T, row R').
Wells named in basin tables are stored as wells without coordinates (position_source=None), field = basin.
"""
from __future__ import annotations

import hashlib
import html
import re
from collections import Counter
from pathlib import Path

import pdfplumber
from sqlalchemy.orm import Session

from app.config import RAW_DIR
from app.db.models import Basin, Document, Field, Passage, Well
from app.ingest.sodir import split_sentences

INDIA = RAW_DIR / "india"
LICENCE = "Government of India public web content (NDR / DGH, MoPNG) — cited, not redistributed"
NDR_PAGE = "https://www.ndrdgh.gov.in/NDR/?page_id={}"
PAGE_IDS = {"krishna-godavari": 647, "mumbai-offshore": 651, "assam-arakan": 617, "rajasthan": 656, "cauvery": 640, "cambay": 629,
            "saurashtra": 822, "kutch": 742, "vindhyan": 831, "mahanadi": 759, "andaman-nicobar": 790, "kerala-konkan": 814,
            "bengal-purnea": 797, "ganga-punjab": 1092, "pranhita-godavari": 879, "satpura-south-rewa-damodar": 886,
            "himalayan-foreland": 808, "chhattisgarh": 853, "spiti-zanskar": 891, "deccan-syneclise": 866, "cuddapah": 860,
            "karewa": 873, "bhima-kaladgi": 846}
PAPERS = {"ndr_paper_01.pdf": "https://www.ndrdgh.gov.in/NDR/pdf/01.pdf", "ndr_paper_03.pdf": "https://www.ndrdgh.gov.in/NDR/pdf/03.pdf",
          "ndr_paper_05.pdf": "https://www.ndrdgh.gov.in/NDR/pdf/05.pdf", "ndr_paper_06.pdf": "https://www.ndrdgh.gov.in/NDR/pdf/06.pdf",
          "ndr_paper_07.pdf": "https://www.ndrdgh.gov.in/NDR/pdf/07.pdf", "ndr_geoscientific_policy.pdf": "https://www.ndrdgh.gov.in/NDR/pdf/Geo-scientific_Policy.pdf"}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_basin_page(h: str) -> dict:
    i = h.find("blog_post_content")
    c = h[h.find(">", i) + 1:] if i >= 0 else h
    end = c.find("</article>")
    c = c[: end if end > 0 else len(c)]
    c = re.sub(r"<script.*?</script>|<style.*?</style>", "", c, flags=re.S)
    tables = []
    for t in re.findall(r"<table.*?</table>", c, flags=re.S):
        rows = [[_clean(x) for x in re.findall(r"<t[dh].*?</t[dh]>", r, flags=re.S)] for r in re.findall(r"<tr.*?</tr>", t, flags=re.S)]
        tables.append([r for r in rows if any(r)])
    body = re.sub(r"<table.*?</table>", "\n", c, flags=re.S)
    paras = [p for p in (_clean(x) for x in re.split(r"(?i)</p>|<br\s*/?>|</h\d>|</li>|</div>", body)) if len(p) > 2]
    title = paras[0] if paras else ""
    return {"title": title, "paras": paras, "tables": tables}


def _num(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", s)
    return float(m.group(1).replace(",", "")) if m else None


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    bdir = INDIA / "basins"
    if not bdir.exists():
        log("india: no data/raw/india/basins — run scripts/download_india.sh")
        return {}
    fld_cache: dict[str, Field] = {}
    for f in sorted(bdir.glob("*.html")):
        key = f.stem
        d = parse_basin_page(f.read_text(encoding="utf-8", errors="ignore"))
        url = NDR_PAGE.format(PAGE_IDS.get(key, ""))
        name = d["title"] or key.replace("-", " ").title()
        text_all = " ".join(d["paras"])
        area_sent = next((x for p in d["paras"] for x in split_sentences(p)
                          if re.search(r"(?i)\b(covers|area of|total area)\b", x) and re.search(r"(?i)sq\.?\s*km|km2", x)
                          and not re.search(r"(?i)survey|mapping|LKM|SKM", x)), None)
        area_nums = re.findall(r"([\d,]{3,}(?:\.\d+)?)\s*(?:sq\.?\s*km|sq km|km2)", area_sent or "", re.I)
        m_wells = re.search(r"(?:more than|about|total of)?\s*([\d,]{2,})\s+exploratory wells", text_all, re.I)
        cat = None
        for i, p in enumerate(d["paras"]):
            if re.match(r"(?i)^category of the basin", p):
                nxt = re.sub(r"(?i)^category of the basin\s*:?\s*", "", p) or (d["paras"][i + 1] if i + 1 < len(d["paras"]) else "")
                m = re.search(r"\b(Category[- ]?(?:I{1,3}|IV)|Proved|Prospective|Potential)\b", nxt, re.I)
                cat = m.group(1) if m else None
                break
        if cat is None:
            m = re.search(r"\b(Category[- ]?(?:I{1,3}|IV))\b", text_all)
            cat = m.group(1) if m else None
        bb = re.search(r"latitudes?\s+(\d+)\s*[˚°]\s*(\d+)?\D{1,6}and\s+(\d+)\s*[˚°]\s*(\d+)?\D{1,10}longitudes?\s+(\d+)\s*[˚°]\s*(\d+)?\D{1,6}and\s+(\d+)\s*[˚°]\s*(\d+)?", text_all)
        bbox = None
        if bb:
            g = [int(x) if x else 0 for x in bb.groups()]
            bbox = [g[4] + g[5] / 60, g[0] + g[1] / 60, g[6] + g[7] / 60, g[2] + g[3] / 60]  # minLon, minLat, maxLon, maxLat
        doc = Document(well_id=None, kind="BASIN_REPORT", title=f"NDR basin summary — {name}", url=url, path=str(f.relative_to(RAW_DIR.parent)),
                       licence=LICENCE, sha256=f"ndr-basin-{key}")
        db.add(doc)
        db.flush()
        seq = 0
        for pi, p in enumerate(d["paras"], start=1):
            for si, s in enumerate(split_sentences(p), start=1):
                seq += 1
                db.add(Passage(document_id=doc.id, well_id=None, locator=f"para {pi}.s{si}", seq=seq, text=s))
        for ti, t in enumerate(d["tables"], start=1):
            head = t[0] if t else []
            for ri, row in enumerate(t[1:] if len(t) > 1 else t, start=1):
                txt = " | ".join(f"{h}: {v}" if h and h != v else v for h, v in zip(head + [""] * len(row), row) if v)
                if txt:
                    seq += 1
                    db.add(Passage(document_id=doc.id, well_id=None, locator=f"table {ti}, row {ri}", seq=seq, text=txt[:2000]))
        stats["passages"] += seq
        b = Basin(name=name, slug=key, url=url, category=cat,
                  area_sqkm=_num(area_nums[0]) if len(area_nums) == 1 else None, area_text=area_sent, exploratory_wells=_num(m_wells.group(1)) if m_wells else None,
                  bbox=bbox, document_id=doc.id, n_tables=len(d["tables"]))
        db.add(b)
        stats["basins"] += 1
        # wells listed in tables (e.g. 'Well Name | Drilled Depth(m)')
        for ti, t in enumerate(d["tables"], start=1):
            if not t:
                continue
            head = [h.lower() for h in t[0]]
            wi = next((i for i, h in enumerate(head) if h.startswith("well")), None)
            if wi is None:
                continue
            di = next((i for i, h in enumerate(head) if "depth" in h), None)
            oi = next((i for i, h in enumerate(head) if "operator" in h), None)
            if key not in fld_cache:
                fld_cache[key] = Field(name=f"{name} (India)", country="India", source="ndr_dgh")
                db.add(fld_cache[key])
                db.flush()
            for ri, row in enumerate(t[1:], start=1):
                if wi >= len(row) or not row[wi] or len(row[wi]) > 60 or not re.search(r"\d", row[wi]):
                    continue
                wname = f"IN-{key.upper()[:6]}: {row[wi]}"
                if db.query(Well).filter(Well.canonical_name == wname).first():
                    continue
                db.add(Well(canonical_name=wname, aliases=[row[wi]], field_id=fld_cache[key].id, field_name=f"{name} (India)", country="India",
                            lat=None, lon=None, td_md_m=_num(row[di]) if di is not None and di < len(row) else None,
                            operator=row[oi] if oi is not None and oi < len(row) else None, source="ndr_india",
                            position_source=None, fact_url=url, purpose="listed in NDR basin summary"))
                stats["india_wells_listed"] += 1
    # technical papers / policies
    for fn, url in PAPERS.items():
        p = INDIA / fn
        if not p.exists():
            continue
        try:
            with pdfplumber.open(p) as pdf:
                pages = [pg.extract_text() or "" for pg in pdf.pages]
        except Exception as e:  # noqa: BLE001
            log(f"india: cannot read {fn}: {e}")
            continue
        title = next((l.strip() for l in pages[0].split("\n") if len(l.strip()) > 25), fn)
        doc = Document(well_id=None, kind="PAPER", title=f"NDR/DGH — {title[:150]}", url=url, path=str(p.relative_to(RAW_DIR.parent)),
                       pages=len(pages), licence=LICENCE, sha256=hashlib.sha256("".join(pages).encode()).hexdigest())
        db.add(doc)
        db.flush()
        seq = 0
        for pi, t in enumerate(pages, start=1):
            for li, par in enumerate(re.split(r"\n\s*\n|(?<=[.])\n", t), start=1):
                par = re.sub(r"\s+", " ", par).strip()
                if len(par) < 40:
                    continue
                seq += 1
                db.add(Passage(document_id=doc.id, well_id=None, locator=f"page {pi}, para {li}", seq=seq, text=par[:1500]))
        stats["papers"] += 1
        stats["passages"] += seq
    db.flush()
    log(f"india: {dict(stats)}")
    return dict(stats)
