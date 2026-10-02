"""Add more NLOG (Netherlands) well reports to an existing database, without a full rebuild.

Why: NLOG has public well reports for 6,737 Dutch wells and 6,486 of them already have formation tops in the
database, but only 117 report PDFs were sampled at first. Each report adds real recorded problems (events) to
learn from and to test against in the Hindsight blind test.

Phases (each resumable; run them in order or all at once):
    python -m scripts.add_nlog_reports select   [--max-reports 1000] [--max-gb 1.5]
    python -m scripts.add_nlog_reports download
    python -m scripts.add_nlog_reports load      # ingest new PDFs -> extraction -> episodes -> sources
    python -m scripts.add_nlog_reports all

Selection rule (decided before looking at any result): wells with formation tops and no report yet, spudded
1985 or later (reports more likely digital and narrative), ranked by how many other top-carrying wells lie
within 5 km (so the new wells have offsets and become testable). For each, the best drilling-narrative report
from its NLOG document list, by title priority: end of well / final well / drilling / geological well report.
Public data, no login (Dutch government open data, TNO/EZK). Every file is recorded in MANIFEST.csv.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import RAW_DIR
from app.db.models import Document, FormationTop, Well
from app.db.session import SessionLocal

NL = RAW_DIR / "netherlands" / "nlog"
REPORTS = NL / "reports"
PLAN = NL / "more_reports_plan.json"
DOCS_URL = "https://www.nlog.nl/nlog-mapviewer/rest/brh/documents"
FILE_URL = "https://www.nlog.nl/brh-web/rest/brh/document/{bfile}"
LICENCE = "Dutch government open data (TNO/EZK, NLOG) - public, no registration"
PRIORITY = [r"end of well report", r"final well report", r"daily drilling report|drilling report",
            r"geological (final )?well report|final well ?site geological report|geological well summary|well summary"]
MAX_FILE = 25_000_000


def _sanitise(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def _post(url: str, body) -> object:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def select_reports(max_reports: int, max_gb: float, log=print) -> list[dict]:
    headers = {h["boreholeName"].strip(): h for h in json.loads((NL / "nlog_boreholes_headers.json").read_text()) if h.get("boreholeName")}
    with SessionLocal() as db:
        documented = set(db.scalars(select(Document.well_id).where(Document.well_id.is_not(None)).distinct()))
        tops_wells = set(db.scalars(select(FormationTop.well_id).distinct()))
        wells = [w for w in db.scalars(select(Well).where(Well.source == "nlog")) if w.id in tops_wells and w.lat is not None]
    pts = [(w, math.radians(w.lat), math.radians(w.lon)) for w in wells]

    def density(w, la, lo) -> int:  # top-carrying NLOG wells within 5 km
        n = 0
        for w2, la2, lo2 in pts:
            if w2.id != w.id and abs(la2 - la) < 0.0008:
                d = 6371 * math.acos(min(1, math.sin(la) * math.sin(la2) + math.cos(la) * math.cos(la2) * math.cos(lo2 - lo)))
                n += d <= 5
        return n
    cand = [(density(w, la, lo), w) for w, la, lo in pts
            if w.id not in documented and w.spud_date and w.spud_date.year >= 1985]
    cand.sort(key=lambda t: (-t[0], t[1].canonical_name))
    log(f"select: {len(cand)} candidate wells (tops, no report yet, spudded 1985+)")
    plan, total = [], 0
    for i, (dens, w) in enumerate(cand):
        if len(plan) >= max_reports or total >= max_gb * 1e9:
            break
        name = w.canonical_name[4:]
        h = headers.get(name)
        if not h:
            continue
        try:
            docs = _post(DOCS_URL, h["boreholeDbk"])
        except Exception as e:  # noqa: BLE001 - one failing well must not stop the selection
            log(f"select: documents for {name} failed: {e!r}")
            continue
        best = None
        for rank, pat in enumerate(PRIORITY):
            hits = [d for d in docs if d.get("hasBfile") and not d.get("lost") and d.get("fileTypeCode") == "PDF"
                    and d.get("fileSize") and d["fileSize"] <= MAX_FILE and re.search(pat, d.get("fullTitle") or "", re.I)]
            if hits:
                best = min(hits, key=lambda d: d["fileSize"])
                break
        if best:
            plan.append({"boreholeDbk": h["boreholeDbk"], "boreholeName": name, "assetBfileDbk": best["assetBfileDbk"],
                         "fullTitle": best["fullTitle"], "fileSize": best["fileSize"], "neighbours_5km": dens})
            total += best["fileSize"]
        if i % 50 == 0:
            log(f"select: checked {i + 1} wells, {len(plan)} reports chosen, {total / 1e9:.2f} GB")
        time.sleep(0.2)  # be gentle with the public server
    PLAN.write_text(json.dumps(plan))
    log(f"select: {len(plan)} reports, {total / 1e9:.2f} GB -> {PLAN}")
    return plan


def download(log=print) -> list[str]:
    plan = json.loads(PLAN.read_text())
    REPORTS.mkdir(parents=True, exist_ok=True)
    manifest = RAW_DIR / "netherlands" / "MANIFEST.csv"
    done = []

    def one(p):
        path = REPORTS / f"{_sanitise(p['boreholeName'])}__{p['assetBfileDbk']}.pdf"
        if path.exists() and path.stat().st_size > 0:
            return path, False
        tmp = path.with_suffix(".part")
        with urllib.request.urlopen(FILE_URL.format(bfile=p["assetBfileDbk"]), timeout=300) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 16):
                f.write(chunk)
        tmp.replace(path)
        return path, True

    new_rows = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(one, p): p for p in plan}
        for k, fut in enumerate(as_completed(futs), 1):
            p = futs[fut]
            try:
                path, fresh = fut.result()
            except Exception as e:  # noqa: BLE001
                log(f"download: {p['boreholeName']} failed: {e!r}")
                continue
            done.append(str(path))
            if fresh:
                new_rows.append([str(path.relative_to(RAW_DIR / "netherlands")), FILE_URL.format(bfile=p["assetBfileDbk"]), LICENCE,
                                 datetime.now(timezone.utc).isoformat(), f"{p['fullTitle']} ({p['fileSize']} bytes) — well {p['boreholeName']}"])
            if k % 50 == 0:
                log(f"download: {k}/{len(plan)}")
    with open(manifest, "a", newline="") as f:
        csv.writer(f).writerows(new_rows)
    # titles for the ingester (it reads selected_reports.json for report titles)
    sel_p = NL / "selected_reports.json"
    sel = json.loads(sel_p.read_text()) if sel_p.exists() else []
    have = {s["assetBfileDbk"] for s in sel}
    sel += [{k: p[k] for k in ("boreholeDbk", "boreholeName", "assetBfileDbk", "fullTitle", "fileSize")} for p in plan if p["assetBfileDbk"] not in have]
    sel_p.write_text(json.dumps(sel))
    log(f"download: {len(done)} files present, {len(new_rows)} new")
    return done


def load(log=print) -> dict:
    from collections import Counter
    from pathlib import Path

    from app.engines import episodes, post
    from app.extract import pipeline
    from app.ingest.ext import nl_nlog
    plan = json.loads(PLAN.read_text())
    paths = [p for p in (REPORTS / f"{_sanitise(x['boreholeName'])}__{x['assetBfileDbk']}.pdf" for x in plan) if p.exists()]
    with SessionLocal() as db:
        wells = {w.canonical_name: w for w in db.scalars(select(Well).where(Well.source == "nlog"))}
        before = set(db.scalars(select(Document.id)))
        stats = Counter()
        n = nl_nlog.ingest_reports(db, wells, stats, paths=[Path(p) for p in paths], log=log)
        db.commit()
        new_docs = set(db.scalars(select(Document.id))) - before
        new_wells = set(db.scalars(select(Document.well_id).where(Document.id.in_(new_docs)))) - {None}
        log(f"load: {n[0]} new report documents on {len(new_wells)} wells ({dict(stats)})")
        post.assign_countries(db)
        db.commit()
        if new_docs:
            log(f"load: extraction {pipeline.run(db, doc_ids=new_docs)}")
            db.commit()
            log(f"load: episodes {episodes.run(db, well_ids=new_wells)}")
            db.commit()
        post.register_sources(db)
        db.commit()
    return {"documents": n[0], "wells": len(new_wells)}


def main() -> None:
    args = sys.argv[1:]
    phase = args[0] if args else "all"
    mr = int(args[args.index("--max-reports") + 1]) if "--max-reports" in args else 1000
    mg = float(args[args.index("--max-gb") + 1]) if "--max-gb" in args else 1.5
    if phase in ("select", "all"):
        select_reports(mr, mg)
    if phase in ("download", "all"):
        download()
    if phase in ("load", "all"):
        print(load())


if __name__ == "__main__":
    main()
