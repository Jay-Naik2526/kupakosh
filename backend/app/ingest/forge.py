"""Utah FORGE (US DOE Geothermal Data Repository, CC-BY 4.0) -> wells, surveys, DDRs, sensors.

Wells are listed in config/forge_tops.yaml (16A(78)-32, 16B(78)-32, 58-32, 78B-32, 68-32, 78-32).
  * DDR PDFs (vendor formats: WellEz for 16A; RIMBase / Geothermal Resource Group for the others;
    one report per file, or many reports in one PDF for 78B-32) -> document, activity, passage
    (one passage per time-breakdown row, locator 'page N, row K'), mud checks, casing, LOT
  * survey files -> survey_station (vendor minimum-curvature TVD kept; our own min-curvature
    recomputation is checked against it in tests)
  * Pason sensor data (16A, 16B) -> realtime_sample (downsampled, REPLAY source)
Units: reports are in feet / ppg / bbl; depths are stored in metres with raw text kept in the passage.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pdfplumber
import yaml
from sqlalchemy.orm import Session

from app.config import CONFIG_DIR, DATA_DIR, RAW_DIR, cfg
from app.db.models import (Activity, CasingString, Document, Field, FormationTop, MudCheck, Passage, PressureTest, RealtimeSample,
                           SurveyStation, Well)
from app.ingest.units import ft_to_m, sg_to_ppg

FORGE = RAW_DIR / "forge"
LICENCE = "CC-BY 4.0 (US DOE Geothermal Data Repository)"
USFT = 1200 / 3937


def _meta() -> dict:
    return yaml.safe_load((CONFIG_DIR / "forge_tops.yaml").read_text())


def _to_latlon(x_m: float, y_m: float) -> tuple[float, float]:
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:26912", "EPSG:4326", always_xy=True)  # NAD83 / UTM zone 12N
    lon, lat = t.transform(x_m, y_m)
    return lat, lon


def location(loc: dict) -> tuple[float, float]:
    if "lat" in loc:
        return loc["lat"], loc["lon"]
    if "utm_x" in loc:
        return _to_latlon(loc["utm_x"], loc["utm_y"])
    return _to_latlon(loc["easting_usft"] * USFT, loc["northing_usft"] * USFT)


# ---------------------------------------------------------------- DDR parsing
_TIME_ROW_WELLEZ = re.compile(r"^(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})\s+(\d+(?:\.\d+)?)\s+(.*)$")
_TIME_ROW_RIM = re.compile(r"^(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})\s+(\d+\.\d{2})\s+([\d,]+)\s+([A-Z0-9][A-Z0-9-]{0,9})\s+(.*?)(\s+X)?$")
_FT = re.compile(r"([\d,]{2,7})(?:\.\d+)?\s?['’]")
_REPORT_FOR = re.compile(r"Report For\s+(?:\d{1,2}:\d{2}\s*[AP]M\s+)?(\d{1,2}-[A-Za-z]{3}-\d{2})")


def _pdf_text(path: Path, cache: dict) -> list[str]:
    for k in (str(path.resolve()), str(path)):
        if k in cache:
            return cache[k]
    rel = str(path)
    for k in cache:
        if k.endswith(rel.split("raw/forge/")[-1]):
            return cache[k]
    with pdfplumber.open(path) as p:
        pages = [pg.extract_text() or "" for pg in p.pages]
    cache[str(path.resolve())] = pages
    return pages


def _report_date(text: str) -> date | None:
    m = re.search(r"RPT DATE:\s*(\d{1,2}/\d{1,2}/\d{4})", text)
    if m:
        return datetime.strptime(m.group(1), "%m/%d/%Y").date()
    m = _REPORT_FOR.search(text)
    if m:
        return datetime.strptime(m.group(1), "%d-%b-%y").date()
    return None


def _report_md_ft(text: str) -> float | None:
    # "MD/TVD:7294 24 HR FTG:349" — when the MD field is blank the next token is "24 HR", which is not a depth
    m = re.search(r"MD/TVD:\s*([\d,]+)\b(?!\s*HR\b)", text) or re.search(r"Measured Depth \(ft\):\s*([\d,]+)", text)
    return float(m.group(1).replace(",", "")) if m else None


def split_reports(pages: list[str]) -> list[list[str]]:
    """A PDF may hold many daily reports (78B-32). Group consecutive pages by their 'Report For' date."""
    groups: list[list[str]] = []
    cur_key = None
    for t in pages:
        m = _REPORT_FOR.search(t) or re.search(r"RPT DATE:\s*(\S+)", t)
        key = m.group(1) if m else cur_key
        if key != cur_key or not groups:
            groups.append([])
            cur_key = key
        groups[-1].append(t)
    return groups


def _stamp(d: date, hhmm: str, period_start: datetime) -> datetime:
    h, m = map(int, hhmm.split(":"))
    t = datetime.combine(d - timedelta(days=1), datetime.min.time()) + timedelta(hours=h, minutes=m)
    if t < period_start:
        t += timedelta(days=1)
    return t


def parse_activities(pages: list[str], rdate: date, report_md_ft: float | None, period_start_h: int = 6) -> list[dict]:
    """Rows of the time-breakdown / operations-summary table, with continuation lines joined."""
    rows: list[dict] = []
    start = datetime.combine(rdate - timedelta(days=1), datetime.min.time()) + timedelta(hours=period_start_h)
    for pi, text in enumerate(pages, start=1):
        in_table = False
        for line in text.split("\n"):
            s = line.strip()
            if re.match(r"^(TIME BREAKDOWN|Operations Summary)", s):
                in_table = True
                continue
            if not in_table:
                continue
            if re.match(r"^(TOTAL HRS|Management Summary|www\.wellez|Comments|Casing/Tubular|Bit Information|Mud Information|Mud Reports|24 Hr Summary)", s):
                in_table = False
                continue
            m = _TIME_ROW_RIM.match(s)
            if m:
                rows.append(dict(page=pi, t0=m.group(1), t1=m.group(2), hrs=float(m.group(3)),
                                 end_md_ft=float(m.group(4).replace(",", "")), code=m.group(5), text=m.group(6).strip(),
                                 npt=bool(m.group(7))))
                continue
            m = _TIME_ROW_WELLEZ.match(s)
            if m and not s.startswith("FROM"):
                rows.append(dict(page=pi, t0=m.group(1), t1=m.group(2), hrs=float(m.group(3)), end_md_ft=None,
                                 code=None, text=m.group(4).strip(), npt=False))
                continue
            if rows and s and not s.startswith(("FROM", "From To")):
                rows[-1]["text"] += " " + s
    for k, r in enumerate(rows, start=1):
        r["seq"] = k
        r["t_start"] = _stamp(rdate, r["t0"], start)
        r["t_end"] = r["t_start"] + timedelta(hours=r["hrs"])
        if r["code"] is None:
            mm = re.search(r"\b(Production|Intermediate|Surface|Conductor) (?:Drilling|Casing)?\s*(Drilling|Trips|Reaming|Cond Mud & Circ|Fishing|Cementing|Other|Rig Repair|Lost Circulation|Stuck Pipe|Well Control|Logging|Casing)\b", r["text"])
            r["code"] = mm.group(2) if mm else None
            r["phase"] = mm.group(1) if mm else None
        else:
            r["phase"] = None
        depths = [float(x.replace(",", "")) for x in _FT.findall(r["text"]) if x.replace(",", "").isdigit()]
        r["md_ft"] = r["end_md_ft"] or (max(depths) if depths else report_md_ft)
    return rows


def parse_mud(pages: list[str]) -> list[float]:
    text = "\n".join(pages)
    out = []
    m = re.search(r"TIME MW FV[^\n]*\n(\d{1,2}:\d{2})\s+(\d{1,2}\.\d)", text)  # WellEz
    if m:
        out.append(float(m.group(2)))
    for m in re.finditer(r"Mud Pits, Type:[^\n]*\n(\d{1,2}\.\d{1,2})\s", text):  # RIMBase (16B)
        out.append(float(m.group(1)))
    for m in re.finditer(r"^\d{2}-[A-Za-z]{3}-\d{2} \d{1,2}:\d{2} (\d{1,2}\.\d{1,2}) ", text, re.M):  # GRG (58-32, 78B-32)
        out.append(float(m.group(1)))
    return out


def parse_casing(pages: list[str]) -> list[dict]:
    text = "\n".join(pages)
    out = []
    for m in re.finditer(r"^(Conductor|Surface|Intermediate|Production|Liner)\s+(\d+\.\d+)\s+[\d.]+\s+\S+\s+([\d,]+)\s+([\d,]+)\s*$", text, re.M):
        out.append(dict(type=m.group(1), od=float(m.group(2)), shoe_ft=float(m.group(3).replace(",", "")),
                        tvd_ft=float(m.group(4).replace(",", "")), line=m.group(0)))
    m = re.search(r"Last Casing:\s*(\d+\.\d+)\s+at\s+([\d,]+)", text)
    if m:
        out.append(dict(type="Last casing", od=float(m.group(1)), shoe_ft=float(m.group(2).replace(",", "")), tvd_ft=None, line=m.group(0)))
    return out


def parse_lot(pages: list[str]) -> tuple[float, float, str] | None:
    """GRG header: 'Last Casing: 9.625 at 2,172 LOT (lbs/gal): 19.20' -> (emw_ppg, shoe_ft, verbatim)."""
    text = "\n".join(pages)
    m = re.search(r"Last Casing:\s*[\d.]+\s+at\s+([\d,]+)\s+LOT \(lbs/gal\):\s*(\d{1,2}\.\d{1,2})", text)
    if m:
        return float(m.group(2)), float(m.group(1).replace(",", "")), m.group(0)
    return None


# ---------------------------------------------------------------- surveys
def read_survey(well: str) -> pd.DataFrame:
    sv = _meta()["wells"][well]["survey"]
    kind = sv["type"]
    base = FORGE / _meta()["wells"][well]["folder"]
    rows = []
    if kind == "xlsx16A":
        x = pd.read_excel(base / sv["path"], header=None)
        for r in x.itertuples(index=False):
            v = list(r)
            if isinstance(v[1], (int, float)) and not pd.isna(v[1]) and isinstance(v[2], (int, float)) and not pd.isna(v[6]):
                try:
                    rows.append(dict(md=float(v[2]), inc=float(v[3]), azi=float(v[4]), tvd=float(v[6]), ns=float(v[8]), ew=float(v[9])))
                except (TypeError, ValueError):
                    pass
    elif kind == "txt16B":
        for line in (base / sv["path"]).read_text(errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 11 and all(re.match(r"^-?\d+(\.\d+)?$", t) for t in parts[:11]):
                rows.append(dict(md=float(parts[0]), inc=float(parts[1]), azi=float(parts[2]), tvd=float(parts[3]), ns=float(parts[5]), ew=float(parts[7])))
    elif kind == "csv78B":
        x = pd.read_csv(base / sv["path"], header=None, skiprows=1, dtype=str)
        for r in x.itertuples(index=False):
            try:
                md, inc, azi, tvd, ns, ew = (float(str(v).replace(",", "")) for v in r[1:7])
                rows.append(dict(md=md, inc=inc, azi=azi, tvd=tvd, ns=ns, ew=ew))
            except (TypeError, ValueError):
                pass
    elif kind == "pdf_grg":
        with pdfplumber.open(base / sv["path"]) as p:
            for pg in p.pages:
                for line in (pg.extract_text() or "").splitlines():
                    m = re.match(r"^\**[A-Za-z]+\s+([\d,.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d,.]+)\s+(-?[\d,.]+)\s+(-?[\d,.]+)", line)
                    if m:
                        f = [float(g.replace(",", "")) for g in m.groups()]
                        rows.append(dict(md=f[0], inc=f[1], azi=f[2], tvd=f[3], ns=f[4], ew=f[5]))
    return pd.DataFrame(rows).drop_duplicates("md").sort_values("md") if rows else pd.DataFrame(rows)


# ---------------------------------------------------------------- realtime
def load_realtime(folder: str, step_s: int = 30) -> pd.DataFrame:
    cache = DATA_DIR / "processed" / f"realtime_{folder}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    df = _load_realtime(folder, step_s)
    df.to_pickle(cache)
    return df


def _load_realtime(folder: str, step_s: int = 30) -> pd.DataFrame:
    if folder == "16A":
        cols = {"Time": "t", "Total Depth": "md_ft", "Block Position": "block", "Weight on Bit": "wob", "Hookload": "hookload",
                "ROP Depth/Hour": "rop", "Top Drive RPM": "rpm", "Top Drive Torque (ft-lbs)": "torque", "Flow In": "flow_in",
                "Pump Pressure": "spp", "Pit Volume Active": "pit_vol"}
        parts = []
        for ch in pd.read_csv(FORGE / "16A" / "time_10s.csv", usecols=list(cols), chunksize=200_000, low_memory=False):
            ch = ch.rename(columns=cols)
            ch["t"] = pd.to_datetime(ch["t"], format="%m/%d/%y %H:%M", errors="coerce")
            ch["torque"] = ch["torque"] / 1000.0  # ft-lbs -> kft-lb
            ch["bit_ft"] = None
            parts.append(ch)
        df = pd.concat(parts)
        df = df.dropna(subset=["t"]).groupby("t").last().reset_index()  # 16A timestamps are minute-resolution
    else:
        cols = {"YYYY/MM/DD": "d", "HH:MM:SS": "hms", "Hole Depth (feet)": "md_ft", "Bit Depth (feet)": "bit_ft",
                "Rate Of Penetration (ft_per_hr)": "rop", "Weight on Bit (klbs)": "wob", "Rotary RPM (RPM)": "rpm",
                "Top Drive Torque (kft_lb)": "torque", "Standpipe Pressure (psi)": "spp", "Total Pump Output (gal_per_min)": "flow_in",
                "Total Mud Volume (barrels)": "pit_vol", "Hook Load (klbs)": "hookload"}
        parts = []
        with zipfile.ZipFile(FORGE / "16B" / "pason.zip").open("10 Second Data.csv") as fh:
            for ch in pd.read_csv(fh, usecols=list(cols), chunksize=300_000, low_memory=False):
                ch = ch.rename(columns=cols).iloc[:: max(1, step_s // 10)]
                ch["t"] = pd.to_datetime(ch["d"] + " " + ch["hms"], format="%Y/%m/%d %H:%M:%S", errors="coerce")
                parts.append(ch.drop(columns=["d", "hms"]))
        df = pd.concat(parts)
    df = df.replace(-999.25, float("nan"))
    df = df[df["md_ft"].notna() & (df["md_ft"] > 0)]
    return df.sort_values("t")


def _report_files(wm: dict) -> list[Path]:
    base = FORGE / wm["folder"]
    d = wm["ddr"]
    if "file" in d:
        return [base / d["file"]] if (base / d["file"]).exists() else []
    return sorted(p for p in base.glob(d["glob"]) if not any(x in str(p) for x in d.get("exclude", [])))


# ---------------------------------------------------------------- main
def ingest(db: Session, log=print, with_realtime: bool = True) -> dict:
    meta = _meta()
    stats: Counter = Counter()
    cache_p = DATA_DIR / "processed" / "forge_ddr_text.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    n_cache = len(cache)
    fld = Field(name="Utah FORGE", country="USA", source="gdr.openei.org")
    db.add(fld)
    db.flush()
    for name, wm in meta["wells"].items():
        files = _report_files(wm)
        if not files:
            log(f"forge {name}: no report files found — skipped (run scripts/download_data.sh)")
            continue
        lat, lon = location(wm["location"])
        w = Well(canonical_name=name, aliases=[f"FORGE {name}"] + wm.get("aliases", []), field_id=fld.id, field_name="Utah FORGE", country="USA",
                 lat=lat, lon=lon, kb_elev_m=ft_to_m(wm["kb_elev_ft"]) if wm.get("kb_elev_ft") else None, spud_date=wm.get("spud_date"),
                 status="COMPLETED", purpose="GEOTHERMAL (EGS)", well_type="DEVELOPMENT", operator="University of Utah",
                 source="forge", parent_well=name, position_source=wm["location"]["src"], fact_url=wm["source_url"])
        db.add(w)
        db.flush()
        ws = Counter()

        sv = read_survey(name) if wm["survey"]["type"] != "vertical" else pd.DataFrame()
        for r in sv.itertuples(index=False):
            db.add(SurveyStation(well_id=w.id, md_m=ft_to_m(r.md), inc_deg=r.inc, azi_deg=r.azi, tvd_m=ft_to_m(r.tvd),
                                 north_m=ft_to_m(r.ns), east_m=ft_to_m(r.ew)))
        ws["survey_stations"] = len(sv)
        if len(sv):
            w.td_md_m, w.td_tvd_m = ft_to_m(sv.md.max()), ft_to_m(sv.tvd.max())

        seen_hash: set[str] = set()
        seen_lot: set[tuple] = set()
        max_md = 0.0
        all_text = []
        for path in files:
            pages_all = _pdf_text(path, cache)
            all_text.append("\n".join(pages_all))
            groups = split_reports(pages_all) if wm["ddr"].get("file") else [pages_all]
            for gi, pages in enumerate(groups):
                full = "\n".join(pages)
                if "DAILY DRILLING REPORT" not in full.upper():
                    ws["pdf_not_ddr"] += 1
                    continue
                h = hashlib.sha256(full.encode()).hexdigest()
                rdate = _report_date(full)
                if h in seen_hash or rdate is None:
                    ws["duplicate_or_undated"] += 1
                    continue
                seen_hash.add(h)
                md_ft = _report_md_ft(full)
                doc = Document(well_id=w.id, kind="DDR_PDF", title=f"Daily drilling report {rdate.isoformat()} — {name}",
                               path=str(path.relative_to(DATA_DIR)) + (f"#report{gi + 1}" if len(groups) > 1 else ""), url=wm["source_url"],
                               report_date=rdate, pages=len(pages), is_scanned=False, sha256=h, licence=LICENCE,
                               report_md_m=ft_to_m(md_ft) if md_ft else None)
                db.add(doc)
                db.flush()
                ws["ddr_docs"] += 1
                for r in parse_activities(pages, rdate, md_ft):
                    md_m = ft_to_m(r["md_ft"]) if r["md_ft"] else None
                    p = Passage(document_id=doc.id, well_id=w.id, locator=f"page {r['page']}, row {r['seq']}", seq=r["seq"],
                                text=f"{r['t0']}-{r['t1']} ({r['hrs']} h) {r['text']}", md_m=md_m, report_date=rdate)
                    db.add(p)
                    db.flush()
                    db.add(Activity(well_id=w.id, document_id=doc.id, passage_id=p.id, seq=r["seq"], t_start=r["t_start"],
                                    t_end=r["t_end"], md_m=md_m, phase=r["phase"], code=r["code"], state="NPT" if r["npt"] else None,
                                    comment=r["text"]))
                    ws["activities"] += 1
                    max_md = max(max_md, md_m or 0)
                for mw in parse_mud(pages):
                    lo, hi = cfg()["extract"]["mw_range_ppg"]
                    if lo <= mw <= hi and md_ft:
                        db.add(MudCheck(well_id=w.id, md_m=ft_to_m(md_ft), mw_ppg=mw, raw_value=mw, raw_unit="ppg",
                                        mud_type=None, measured=rdate, source_ref=f"doc:{doc.id}#mud"))
                        ws["mud_checks"] += 1
                for cs in parse_casing(pages):
                    db.add(CasingString(well_id=w.id, casing_type=cs["type"], od_in=cs["od"], shoe_md_m=ft_to_m(cs["shoe_ft"]),
                                        shoe_tvd_m=ft_to_m(cs["tvd_ft"]) if cs["tvd_ft"] else None,
                                        source_ref=f"doc:{doc.id}#casing:{cs['line'][:60]}"))
                    ws["casing_rows"] += 1
                lot = parse_lot(pages)
                if lot and (lot[0], lot[1]) not in seen_lot:  # the same LOT is repeated in every later report header
                    seen_lot.add((lot[0], lot[1]))
                    emw, shoe_ft, raw = lot
                    db.add(PressureTest(well_id=w.id, kind="LOT", md_m=ft_to_m(shoe_ft), emw_ppg=emw, raw_value=emw, raw_unit="ppg",
                                        casing_shoe_md_m=ft_to_m(shoe_ft), source_ref=f"doc:{doc.id}#header"))
                    ws["lot"] += 1
        if not w.td_md_m:
            w.td_md_m = max_md or None
        db.flush()

        # formation tops (verbatim-quote check)
        joined = "\n".join(all_text)
        for t in wm["tops"]:
            ref = "config/forge_tops.yaml (surface)"
            if t.get("quote"):
                if t["quote"] not in joined:
                    log(f"forge: top {t['formation']} for {name} REJECTED — quote not found in reports")
                    ws["tops_rejected"] += 1
                    continue
                hit = db.query(Passage).join(Document).filter(Document.well_id == w.id, Passage.text.contains(t["quote"][:40])).first()
                ref = f"doc:{hit.document_id}#{hit.locator}" if hit else f"forge report text (quote verified): {t['quote'][:60]}"
            db.add(FormationTop(well_id=w.id, formation=t["formation"], level="FORMATION", lithology=t.get("lithology"),
                                top_md_m=ft_to_m(t["top_ft"]), source="forge_ddr", source_ref=ref))
            ws["formation_tops"] += 1
        db.flush()
        tops = sorted(db.query(FormationTop).filter(FormationTop.well_id == w.id).all(), key=lambda x: x.top_md_m)
        for a, b in zip(tops, tops[1:]):
            a.base_md_m = b.top_md_m
        if tops:
            tops[-1].base_md_m = w.td_md_m

        if with_realtime and wm.get("realtime"):
            df = load_realtime(wm["realtime"])
            recs = [dict(well_id=w.id, t=r.t.to_pydatetime(), md_m=ft_to_m(r.md_ft),
                         bit_md_m=ft_to_m(r.bit_ft) if r.bit_ft == r.bit_ft and r.bit_ft is not None else None,
                         rop=_n(r.rop), wob=_n(r.wob), rpm=_n(r.rpm), torque=_n(r.torque), spp=_n(r.spp), flow_in=_n(r.flow_in),
                         pit_vol=_n(r.pit_vol), hookload=_n(r.hookload), mw_in_ppg=None) for r in df.itertuples(index=False)]
            db.bulk_insert_mappings(RealtimeSample, recs)
            ws["realtime_samples"] = len(recs)
        log(f"forge {name}: {dict(ws)}")
        stats.update(ws)
        stats["wells"] += 1
    if len(cache) != n_cache:
        cache_p.write_text(json.dumps(cache))
    db.flush()
    return dict(stats)


def _n(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f
