"""Post-extraction steps that depend on events (formation for LOT/casing, data-source register)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import CasingString, DataSource, Document, Event, PressureTest, RealtimeSample, Well
from app.engines.formations import TopIndex


def run(db: Session, log=print):
    tops = TopIndex(db)
    for pt in db.scalars(select(PressureTest)):
        pt.formation = tops.at(pt.well_id, pt.md_m)
    for cs in db.scalars(select(CasingString)):
        cs.formation = tops.at(cs.well_id, cs.shoe_md_m)
    db.flush()
    log("post: formations assigned to LOT/FIT and casing shoes")


BUILTIN_RAW_COUNTRY = {"sodir": "Norway", "forge": "USA", "india": "India"}


def assign_countries(db: Session, log=print):
    """Document.country: the country of its well; otherwise the country of the raw-data folder it came from
    (built-in sources + each plug-in's SOURCE["raw_dir"]). Wells without a country inherit nothing (left unknown)."""
    from app.ingest import ext
    by_dir = dict(BUILTIN_RAW_COUNTRY)
    for m in ext.modules():
        src = getattr(m, "SOURCE", {})
        if src.get("raw_dir") and src.get("country"):
            by_dir[src["raw_dir"].strip("/").split("/")[0]] = src["country"]
    wc = dict(db.execute(select(Well.id, Well.country)).all())
    n = 0
    for d in db.scalars(select(Document)):
        c = wc.get(d.well_id) if d.well_id else None
        if not c and d.path:
            parts = d.path.replace("\\", "/").split("/")
            if "raw" in parts and parts.index("raw") + 1 < len(parts):
                c = by_dir.get(parts[parts.index("raw") + 1])
        d.country = c
        n += c is not None
    db.flush()
    log(f"post: country set on {n} documents")


def register_sources(db: Session):
    """Data-source register shown on the Accuracy page (records counted from the DB, not typed in)."""
    from sqlalchemy import delete
    n = lambda *w: db.scalar(select(func.count()).select_from(Document).where(*w)) or 0
    sodir_wells = db.scalar(select(func.count()).select_from(Well).where(Well.source == "sodir")) or 0
    forge_rt = db.scalar(select(func.count()).select_from(RealtimeSample)) or 0
    rows = [
        DataSource(name="Sodir FactPages — wellbores, formation tops, casing & LOT, mud, well history", url="https://factpages.sodir.no",
                   licence="NLOD 2.0", records=sodir_wells, notes=f"{n(Document.kind == 'WELL_HISTORY')} well-history documents"),
        DataSource(name="Utah FORGE 58-32, 78B-32, 68-32, 78-32 drilling data (GDR 1006, 1330, 1153)", url="https://gdr.openei.org/submissions/1330",
                   licence="CC-BY 4.0", records=n(Document.kind == "DDR_PDF", Document.well_id.in_(select(Well.id).where(Well.canonical_name.in_(["58-32", "78B-32", "68-32", "78-32"])))),
                   notes="daily drilling reports, surveys, LOT — offset wells for the 16B replay"),
        DataSource(name="Utah FORGE 16A(78)-32 drilling data (GDR 1283)", url="https://gdr.openei.org/submissions/1283", licence="CC-BY 4.0",
                   records=n(Document.kind == "DDR_PDF", Document.well_id.in_(select(Well.id).where(Well.canonical_name == "16A(78)-32"))),
                   notes="daily drilling reports (PDF), survey, 10 s Pason sensor data"),
        DataSource(name="Utah FORGE 16B(78)-32 drilling data (GDR 1516)", url="https://gdr.openei.org/submissions/1516", licence="CC-BY 4.0",
                   records=n(Document.kind == "DDR_PDF", Document.well_id.in_(select(Well.id).where(Well.canonical_name == "16B(78)-32"))),
                   notes="daily drilling reports (PDF), survey, 10 s Pason sensor data"),
        DataSource(name="NDR / DGH India — 23 sedimentary-basin summaries, technical papers, data policies", url="https://www.ndrdgh.gov.in/NDR/",
                   licence="Govt. of India public web content (cited, not redistributed)",
                   records=n(Document.kind.in_(["BASIN_REPORT", "PAPER"])),
                   notes="real Indian geology, fields and exploration facts; no well-level daily reports (those need NDR registration)"),
        DataSource(name="Rig sensor samples (FORGE 16A and 16B, downsampled)", url="https://gdr.openei.org", licence="CC-BY 4.0",
                   records=forge_rt, notes="REPLAY source for the Command screen"),
    ]
    # only replace our own rows; plug-in ingesters (app/ingest/ext) register their own sources
    db.execute(delete(DataSource).where(DataSource.name.in_([r.name for r in rows])))
    db.add_all(rows)
    db.flush()
