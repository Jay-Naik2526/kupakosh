"""FORCE 2020 lithology competition -> dominant-lithology intervals + caliper-washout evidence.

Source: bolgebrygg/Force-2020-Machine-Learning-competition (GitHub), data also mirrored on
Zenodo (DOI 10.5281/zenodo.4351156). 98 Norwegian wells of digital well logs (GR, RHOB, NPHI,
DTC, CALI, BS, ...) with per-sample lithology labels (FORCE_2020_LITHOFACIES_LITHOLOGY) and
NPD GROUP/FORMATION labels, split across train.zip (train.csv), leaderboard_test_features.csv +
leaderboard_test_target.csv, and hidden_test.csv. Licence: NLOD 2.0 / CC-BY 4.0 (the underlying
data is Norwegian public-sector well-log data; the competition repo redistributes it CC-BY 4.0 -
see readme.md in data/raw/force2020/).

SPEC.md forbids adding new ORM models here, so this module reuses two existing tables:
  * FormationTop(level="LITHOLOGY", ...) for contiguous depth intervals of the dominant lithology
    label (short runs merged into a neighbour so counts stay sane - MIN_INTERVAL_M below).
  * Document(kind="OTHER") + Passage for caliper-washout evidence (CALI - BS beyond a threshold,
    sustained over a minimum length). kind="OTHER" is deliberate: these passages are evidence-only
    and must NOT be swept into the DDR/WCR hazard-extraction pipeline, which only reads document
    kinds DDR_*/WCR_*/EOWR_*/MUDLOG.

Every well is matched to the existing Sodir Well row via app.ingest.well_ids.canonical(); a Well is
only created here when no such row exists (country="Norway", source="force2020", lat/lon from the
dataset's X_LOC/Y_LOC columns when present).
"""
from __future__ import annotations

import io
import zipfile
from collections import Counter, defaultdict

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import RAW_DIR
from app.db.models import DataSource, Document, FormationTop, Passage, Well
from app.ingest.well_ids import canonical

SOURCE = {
    "name": "FORCE 2020 lithology competition",
    "country": "Norway",
    "url": "https://github.com/bolgebrygg/Force-2020-Machine-Learning-competition "
           "(data: https://doi.org/10.5281/zenodo.4351156)",
    "licence": "NLOD 2.0 / CC-BY 4.0",
    "raw_dir": "force2020",
}

FORCE2020 = RAW_DIR / "force2020"
LICENCE = SOURCE["licence"]

MIN_INTERVAL_M = 5.0          # lithology runs shorter than this are merged into a neighbouring run
WASHOUT_THRESHOLD_IN = 2.0    # CALI - BS beyond this many inches flags a washout
WASHOUT_MIN_LEN_M = 5.0       # ... sustained over at least this much MD

# Official code -> name key, published in the competition's data/starter_notebook.ipynb
LITHOLOGY_KEY = {
    30000: "Sandstone", 65030: "Sandstone/Shale", 65000: "Shale", 80000: "Marl",
    74000: "Dolomite", 70000: "Limestone", 70032: "Chalk", 88000: "Halite",
    86000: "Anhydrite", 99000: "Tuff", 90000: "Coal", 93000: "Basement",
}

_COLS = ["WELL", "DEPTH_MD", "X_LOC", "Y_LOC", "CALI", "BS", "FORCE_2020_LITHOFACIES_LITHOLOGY"]


def _load_frame(name: str, log) -> pd.DataFrame | None:
    """Load one FORCE 2020 split into a common frame with columns in _COLS, or None if absent."""
    if name == "train.zip":
        p = FORCE2020 / "train.zip"
        if not p.exists():
            return None
        with zipfile.ZipFile(p) as z:
            inner = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
            if inner is None:
                log(f"force2020: train.zip has no CSV member")
                return None
            with z.open(inner) as f:
                df = pd.read_csv(io.TextIOWrapper(f, encoding="utf-8"), sep=";", low_memory=False)
        df["__file"] = f"train.zip:{inner}"
        return df

    if name == "hidden_test.csv":
        p = FORCE2020 / "hidden_test.csv"
        if not p.exists():
            return None
        df = pd.read_csv(p, sep=";", low_memory=False)
        df["__file"] = "hidden_test.csv"
        return df

    if name == "leaderboard_test.csv":
        pf = FORCE2020 / "leaderboard_test_features.csv"
        pt = FORCE2020 / "leaderboard_test_target.csv"
        if not (pf.exists() and pt.exists()):
            return None
        feats = pd.read_csv(pf, sep=";", low_memory=False)
        target = pd.read_csv(pt, sep=";", low_memory=False)
        df = feats.merge(target, on=["WELL", "DEPTH_MD"], how="left")
        df["__file"] = "leaderboard_test_features.csv+leaderboard_test_target.csv"
        return df

    return None


def _runs(depths: list[float], codes: list, min_len: float) -> list[list]:
    """Run-length-encode a sorted (depth, code) series, merging runs shorter than min_len."""
    runs: list[list] = []
    for d, c in zip(depths, codes):
        if runs and runs[-1][2] == c:
            runs[-1][1] = d
        else:
            runs.append([d, d, c])
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i, (s, e, c) in enumerate(runs):
            if e - s < min_len:
                if i < len(runs) - 1:
                    runs[i + 1][0] = s
                else:
                    runs[i - 1][1] = e
                del runs[i]
                changed = True
                break
        merged: list[list] = []
        for r in runs:
            if merged and merged[-1][2] == r[2]:
                merged[-1][1] = r[1]
            else:
                merged.append(list(r))
        runs = merged
    return runs


def _washout_runs(depths: list[float], cali: list, bs: list, thresh: float, min_len: float) -> list[tuple]:
    """Contiguous MD spans where CALI - BS > thresh, sustained over >= min_len. Returns (start, end, min_d, max_d)."""
    flags = []
    for d, ca, b in zip(depths, cali, bs):
        ok = pd.notna(ca) and pd.notna(b) and (ca - b) > thresh
        flags.append((d, (ca - b) if ok else None, ok))
    spans = []
    cur = None
    for d, diff, ok in flags:
        if ok:
            if cur is None:
                cur = [d, d, diff, diff]
            else:
                cur[1] = d
                cur[2] = min(cur[2], diff)
                cur[3] = max(cur[3], diff)
        else:
            if cur is not None:
                spans.append(tuple(cur))
                cur = None
    if cur is not None:
        spans.append(tuple(cur))
    return [s for s in spans if s[1] - s[0] >= min_len]


def _to_latlon(x: float, y: float) -> tuple[float, float]:
    """FORCE 2020 X_LOC/Y_LOC are documented as UTM easting/northing; NPD-era Norwegian sector
    coordinates of this vintage are ED50 / UTM zone 31N (EPSG:23031) - verified against known
    Volve well 15/9-14 (423244.5, 6461862.5) -> ~58.29N 1.69E, matching the real block 15/9
    location. Recorded as an assumption in position_source."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:23031", "EPSG:4326", always_xy=True)
    lon, lat = t.transform(x, y)
    return lat, lon


def ingest(db: Session, log=print) -> dict:
    stats: Counter = Counter()
    if not FORCE2020.exists():
        log("force2020: data/raw/force2020 missing, skipping")
        return dict(stats)

    frames = []
    for split in ("train.zip", "leaderboard_test.csv", "hidden_test.csv"):
        df = _load_frame(split, log)
        if df is not None:
            frames.append(df)
    if not frames:
        log("force2020: no source CSVs found under data/raw/force2020, skipping")
        return dict(stats)

    seen_wells: set[str] = set()
    for df in frames:
        file_label = df["__file"].iloc[0]
        df = df.reset_index(drop=True)
        df["__row"] = df.index + 2  # +2: header is CSV line 1, first data row is line 2
        for col in ("X_LOC", "Y_LOC", "CALI", "BS", "FORCE_2020_LITHOFACIES_LITHOLOGY", "DEPTH_MD"):
            if col not in df.columns:
                df[col] = pd.NA

        for well_name, wdf in df.groupby("WELL"):
            name = canonical(str(well_name))
            if name in seen_wells:
                stats["wells_skipped_duplicate_split"] += 1
                continue
            seen_wells.add(name)
            wdf = wdf.sort_values("DEPTH_MD")
            stats["rows"] += len(wdf)

            well = db.scalars(select(Well).where(Well.canonical_name == name)).first()
            if well is None:
                lat = lon = None
                pos_src = None
                xy = wdf.dropna(subset=["X_LOC", "Y_LOC"])
                if len(xy):
                    x0, y0 = float(xy["X_LOC"].iloc[0]), float(xy["Y_LOC"].iloc[0])
                    try:
                        lat, lon = _to_latlon(x0, y0)
                        pos_src = f"force2020 X_LOC/Y_LOC ({file_label}), assumed ED50/UTM31N (EPSG:23031)"
                    except Exception as e:
                        log(f"force2020: {name} coordinate conversion failed: {e!r}")
                well = Well(canonical_name=name, aliases=[str(well_name)], country="Norway",
                            lat=lat, lon=lon, source="force2020", position_source=pos_src)
                db.add(well)
                db.flush()
                stats["wells_created"] += 1
            else:
                stats["wells_matched"] += 1

            # ---- lithology intervals -> FormationTop(level="LITHOLOGY")
            lit = wdf.dropna(subset=["FORCE_2020_LITHOFACIES_LITHOLOGY"])
            if len(lit):
                depths = lit["DEPTH_MD"].astype(float).tolist()
                codes = lit["FORCE_2020_LITHOFACIES_LITHOLOGY"].astype(float).astype(int).tolist()
                rows = lit["__row"].tolist()
                # keep a row->depth lookup so a merged run can cite the true first/last CSV rows
                row_by_depth = dict(zip(depths, rows))
                runs = _runs(depths, codes, MIN_INTERVAL_M)
                for start, end, code in runs:
                    litho_name = LITHOLOGY_KEY.get(code, f"unknown-code-{code}")
                    r_lo = min(row_by_depth.get(d, 10**9) for d in depths if start <= d <= end)
                    r_hi = max(row_by_depth.get(d, 0) for d in depths if start <= d <= end)
                    db.add(FormationTop(
                        well_id=well.id, formation=litho_name, level="LITHOLOGY",
                        top_md_m=round(start, 2), base_md_m=round(end, 2),
                        source="force2020", source_ref=f"force2020:{file_label}#rows {r_lo}-{r_hi}",
                    ))
                    stats["lithology_intervals"] += 1

            # ---- caliper washout -> Document(kind=OTHER) + Passage (evidence-only, not hazard-extracted)
            cal = wdf.dropna(subset=["CALI", "BS"])
            if len(cal):
                depths = cal["DEPTH_MD"].astype(float).tolist()
                cali = cal["CALI"].astype(float).tolist()
                bs = cal["BS"].astype(float).tolist()
                rows = cal["__row"].tolist()
                spans = _washout_runs(depths, cali, bs, WASHOUT_THRESHOLD_IN, WASHOUT_MIN_LEN_M)
                if spans:
                    doc = Document(well_id=well.id, kind="OTHER",
                                    title=f"FORCE 2020 log-derived intervals — {name}",
                                    path=f"data/raw/force2020/{file_label.split(':')[0].split('+')[0]}",
                                    licence=LICENCE)
                    db.add(doc)
                    db.flush()
                    stats["washout_documents"] += 1
                    row_by_depth = dict(zip(depths, rows))
                    for seq, (s, e, dmin, dmax) in enumerate(spans, start=1):
                        r_lo = row_by_depth.get(s, "?")
                        r_hi = row_by_depth.get(e, "?")
                        text = (f"Caliper exceeds bit size by {dmin:.1f}–{dmax:.1f} in from "
                                f"{s:.1f} to {e:.1f} m MD (log-derived washout indicator).")
                        db.add(Passage(document_id=doc.id, well_id=well.id, locator=f"rows {r_lo}-{r_hi}",
                                       seq=seq, text=text, md_m=round((s + e) / 2, 2)))
                        stats["washout_passages"] += 1

    total_wells = stats.get("wells_created", 0) + stats.get("wells_matched", 0)
    db.add(DataSource(
        name="FORCE 2020 lithology competition — well-log-derived lithology & caliper evidence",
        url=SOURCE["url"], licence=LICENCE, records=total_wells,
        notes=(f"{stats.get('lithology_intervals', 0)} lithology intervals, "
               f"{stats.get('washout_passages', 0)} caliper-washout passages over {total_wells} wells "
               f"({stats.get('wells_created', 0)} newly created, {stats.get('wells_matched', 0)} matched to Sodir)."
               " NOTE: app.engines.post.register_sources() currently rewrites the whole data_source table"
               " from a hardcoded list on every bootstrap run, so this row is overwritten unless that"
               " function is updated to include ext-module sources."),
    ))
    db.flush()
    log(f"force2020: {dict(stats)}")
    return dict(stats)
