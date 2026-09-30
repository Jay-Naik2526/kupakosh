"""Equinor Volve daily drilling reports (DDRs) -> documents, timed activities and passages.

Source: Equinor's Volve data release (the field's WITSML drillReport objects), as republished on
HuggingFace as `bengsoon/volve_alpaca` (CC-BY-2.0): 1,759 real daily reports from 23 Volve wellbores,
1979-2016. Each record holds the well name, the report date and the rig's timed activity lines
("06:00 - 07:30: Drilled 12 1/4" hole from 2587 m to 2750 m ..."), plus Equinor's own 24-hour summary.

Why it matters: these are true day-by-day reports, the document type the problem statement is about. The
episode linker (app.engines.episodes) can follow a problem through the next days' activities to its
outcome, so "what actually worked" rests on real daily records, not only on well-history summaries.

Rules kept here:
- Nothing is invented. Times come from the activity line; depth only when the line itself states it in
  metres; a formation only when the line names it (see `formation` below), never guessed from a
  neighbouring well.
- Every activity is its own Passage (citable as doc:<id>#<date> hh:mm-hh:mm) and Activity row.
- The raw file is data/raw/volve_ddr/volve_ddr.jsonl (converted once from the published parquet files;
  see data/raw/volve_ddr/README.md).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_DIR
from app.db.models import Activity, Document, FormationTop, Passage, Well
from app.ingest.well_ids import canonical

SOURCE = {
    "name": "Equinor Volve daily drilling reports (via HuggingFace bengsoon/volve_alpaca)",
    "country": "Norway",
    "url": "https://huggingface.co/datasets/bengsoon/volve_alpaca",
    "licence": "CC-BY-2.0 (dataset card); original data: Equinor Volve data release",
    "raw_dir": "volve_ddr",
}

HEAD = re.compile(r"for well (.+?) on (\d{4}-\d{2}-\d{2})")
LINE = re.compile(r"^\s*(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2}):\s*(.+?)\s*$")
# a depth written in metres on the line itself: "to 2750 m", "@ 2345m", "at 1234 m MD"
DEPTH = re.compile(r"(?<![\d.,])(\d{2,4}(?:[.,]\d+)?)\s*m(?:\s*MD)?\b(?!\s*(?:3|³|/|in\b|m\b))", re.I)


def _stamp(d: date, hh: str, mm: str) -> datetime:
    h, m = int(hh), int(mm)
    return datetime(d.year, d.month, d.day) + timedelta(hours=h, minutes=m)  # "24:00" rolls to next day


def _depth(text: str, td: float | None) -> float | None:
    vals = []
    for m in DEPTH.finditer(text):
        v = float(m.group(1).replace(",", "."))
        if 10 <= v <= (td + 50 if td else 6500):
            vals.append(v)
    # the deepest depth on a line is where the bit got to ("RIH to 3661m ... pulling 15m up": 3661, not 15)
    return max(vals) if vals else None


def ingest(db: Session, log=print) -> dict:
    path = DATA_DIR / "raw" / SOURCE["raw_dir"] / "volve_ddr.jsonl"
    if not path.exists():
        log(f"volve_ddr: {path} missing — run backend/scripts/download_world.sh volve_ddr")
        return {"skipped": "raw file missing"}
    wells = {w.canonical_name: w for w in db.scalars(select(Well).where(Well.canonical_name.like("15/9-%")))}
    # formation names that appear in this field's own recorded tops, for "the line names a formation" matching
    names = sorted({t.formation for t in db.scalars(select(FormationTop).join(Well).where(Well.canonical_name.like("15/9-%")))
                    if t.formation}, key=len, reverse=True)
    rock_words = {"CHALK", "SHALE", "CLAY", "SAND", "SANDSTONE", "LIMESTONE", "MARL", "COAL", "SALT", "BASEMENT"}
    # "... from utsira manifold" / "utsira water" is the platform's water supply system, not the formation
    fm_rx = [(n, re.compile(r"\b" + re.escape(re.sub(r"\s+(FM|GP)$", "", n)) + r"\b(?!\s+(?:manifold|pumps?|water|wells?)\b)", re.I)) for n in names
             if len(re.sub(r"\s+(FM|GP)$", "", n)) >= 4 and not n.upper().startswith(("NO FORMAL", "UNDEF"))
             and re.sub(r"\s+(FM|GP)$", "", n).upper() not in rock_words]  # "top of chalk" is a rock word, not a unit
    seen = {h for (h,) in db.execute(select(Document.sha256).where(Document.kind == "DDR_XML"))}
    stats = {"reports": 0, "activities": 0, "with_depth": 0, "with_formation": 0, "unmatched_wells": set(), "duplicates": 0}
    for raw in path.read_text().splitlines():
        r = json.loads(raw)
        m = HEAD.search(r["instruction"])
        if not m:
            continue
        name, day = canonical(m.group(1)), date.fromisoformat(m.group(2))
        w = wells.get(name)
        if w is None:
            stats["unmatched_wells"].add(m.group(1))
            continue
        h = hashlib.sha256((name + day.isoformat() + r["input"]).encode()).hexdigest()
        if h in seen:
            stats["duplicates"] += 1
            continue
        seen.add(h)
        lines = [LINE.match(x) for x in r["input"].splitlines()]
        lines = [x for x in lines if x]
        depths = [d for d in (_depth(x.group(5), w.td_md_m) for x in lines) if d is not None]
        doc = Document(well_id=w.id, kind="DDR_XML", title=f"Daily drilling report {day.isoformat()} — {name}",
                       path=f"raw/volve_ddr/volve_ddr.jsonl#{name}@{day.isoformat()}", url=SOURCE["url"], report_date=day,
                       pages=1, is_scanned=False, sha256=h, licence=SOURCE["licence"],
                       report_md_m=max(depths) if depths else None)
        db.add(doc)
        db.flush()
        stats["reports"] += 1
        if r.get("output"):  # Equinor's own 24-hour summary, kept as its own citable passage
            db.add(Passage(document_id=doc.id, well_id=w.id, locator=f"{day.isoformat()} 24-hour summary", seq=0,
                           text=r["output"].strip(), report_date=day))
        for seq, x in enumerate(lines, start=1):
            text = x.group(5)
            t0, t1 = _stamp(day, x.group(1), x.group(2)), _stamp(day, x.group(3), x.group(4))
            md = _depth(text, w.td_md_m)
            fm = next((n for n, rx in fm_rx if rx.search(text)), None)
            p = Passage(document_id=doc.id, well_id=w.id, locator=f"{day.isoformat()} {x.group(1)}:{x.group(2)}-{x.group(3)}:{x.group(4)}",
                        seq=seq, text=f"{x.group(1)}:{x.group(2)}-{x.group(3)}:{x.group(4)} {text}", md_m=md, report_date=day)
            db.add(p)
            db.flush()
            db.add(Activity(well_id=w.id, document_id=doc.id, passage_id=p.id, seq=seq, t_start=t0, t_end=t1, md_m=md,
                            comment=text, formation=fm))
            stats["activities"] += 1
            stats["with_depth"] += md is not None
            stats["with_formation"] += fm is not None
    stats["unmatched_wells"] = sorted(stats["unmatched_wells"])
    log(f"volve_ddr: {stats}")
    return stats
