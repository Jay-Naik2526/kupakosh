"""Pre-drill brief (SPEC.md §9.12): data assembly + official-office-document HTML/PDF."""
from __future__ import annotations

import html
from collections import defaultdict
from datetime import date
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import DATA_DIR, cfg, taxonomy
from app.db.models import AuditFlag
from app.engines import hazard as hz
from app.engines import mudwindow as mw
from app.engines.context import ctx
from app.engines.formations import pretty
from app.engines.lookahead import _fixes
from app.engines.offsets import find_offsets
from app.wiki.compiler import ACTION_LABEL

SEQ = DATA_DIR / "processed" / "brief_seq.txt"


def _next_ref(peek: bool) -> str:
    n = int(SEQ.read_text()) if SEQ.exists() else 0
    if not peek:
        n += 1
        SEQ.parent.mkdir(parents=True, exist_ok=True)
        SEQ.write_text(str(n))
    return f"{cfg()['ui']['file_prefix']}/PDB/{date.today().year}/{max(n, 1) if not peek else n + 1:03d}"


def build(db: Session, lat: float, lon: float, target_td_m: float, planned_tops: list[dict] | None = None,
          radius_m: float | None = None, final: bool = False) -> dict:
    cx = ctx()
    radius_m = radius_m or cfg()["offsets"]["default_radius_m"]
    offs_geo = find_offsets(lat, lon, radius_m, td_m=target_td_m)
    documented = [o for o in offs_geo if o["documented"]]
    # formation column: planned tops, or inferred from the 3 most similar documented offsets that have tops
    inferred = False
    if planned_tops:
        tops = sorted(({"formation": t["formation"], "top_md_m": float(t["top_md_m"])} for t in planned_tops), key=lambda t: t["top_md_m"])
    else:
        inferred = True
        donors = [o for o in documented if cx.tops.tops(o["well_id"])][:3]
        acc = defaultdict(list)
        for o in donors:
            for t in cx.tops.tops(o["well_id"]):
                if t.level == "FORMATION" and t.top_md_m is not None and t.top_md_m <= target_td_m:
                    acc[t.formation].append(t.top_md_m)
        tops = sorted(({"formation": f, "top_md_m": round(median(v)), "n_wells": len(v)} for f, v in acc.items()), key=lambda t: t["top_md_m"])
    forms = [t["formation"] for t in tops]
    offs = find_offsets(lat, lon, radius_m, formations=set(forms), td_m=target_td_m)
    offset_ids = [o["well_id"] for o in offs]
    hazards = []
    for t in tops:
        for hkey in taxonomy()["hazards"]:
            p = hz.posterior(t["formation"], hkey, offs)
            if p["n_with_event"] == 0 and p["status"] == "ok" and p["mean"] < cfg()["hazard"]["alert_threshold"] / 2:
                continue
            if p["n_with_event"] == 0:
                continue
            fx = _fixes(db, hkey, t["formation"], offset_ids)
            hazards.append({**{k: p[k] for k in ("formation", "hazard", "label", "status", "mean", "ci", "n_eff", "n_wells", "n_with_event")},
                            "formation_label": pretty(t["formation"]), "top_md_m": t["top_md_m"],
                            "fix_scope": fx["scope"], "fixes": [{"action": ACTION_LABEL.get(r["action"], r["action"]), "k": r["k"], "n": r["n"],
                                                                 "lb": r["lb"], "worsened": r["worsened"], "anecdotal": r["anecdotal"]} for r in fx["rows"]],
                            "sources": [e for ev in p["evidence"] for e in ev["events"]][:4]})
    mwin = mw.window(db, offset_ids, None)
    mrows = [r for r in mwin["formations"] if r["formation"] in forms]
    lessons = [r for r in mw.casing_lessons(db, offset_ids) if r["formation"] in forms and r["cement_issues"]][:8]
    audits = db.scalars(select(AuditFlag).where(AuditFlag.well_id.in_(offset_ids), AuditFlag.status == "open")).all()
    refs = []
    for h in hazards:
        refs += [s["source_ref"] for s in h["sources"]]
    for r in mrows:
        refs += [e["source_ref"] for e in (r["upper_evidence"] + r["lower_evidence"])[:3]]
    return {
        "ref_no": _next_ref(peek=not final), "date": date.today().isoformat(),
        "subject": f"Pre-drill offset-well brief for proposed location {lat:.5f} N, {lon:.5f} E, target depth {target_td_m:,.0f} m MD",
        "distribution": ["Drilling Superintendent", "Well Planning Engineer", "Geology & Reservoir", "HSE"],
        "inputs": {"lat": lat, "lon": lon, "target_td_m": target_td_m, "radius_m": radius_m, "tops_inferred": inferred},
        "offsets": [{"name": o["name"], "distance_m": o["raw"]["distance_m"], "sim": o["sim"], "documented": o["documented"], "n_events": o["n_events"]} for o in offs[:12]],
        "n_offsets": len(offs), "n_documented": sum(1 for o in offs if o["documented"]),
        "formations": [{**t, "label": pretty(t["formation"])} for t in tops],
        "hazards": sorted(hazards, key=lambda h: (h["top_md_m"], -h["mean"])),
        "mud_window": [{k: r[k] for k in ("formation", "label", "lower_ppg", "upper_ppg", "status", "top_md_m", "used_p10_p90")} for r in mrows],
        "casing_lessons": lessons,
        "audit": [{"well": cx.wells[a.well_id].canonical_name if a.well_id in cx.wells else None, "rule": a.rule, "delta": a.delta,
                   "ref_a": a.ref_a, "ref_b": a.ref_b} for a in audits][:10],
        "sources": list(dict.fromkeys(refs))[:40],
        "disclaimer": "Decision support only. The engineer decides.",
        "data_note": "Data: public Sodir (Norway) and Utah FORGE (USA) records used as stand-ins; not Oil India data.",
        "signatures": [{"role": "Prepared", "name": "Kupakosh (system)"}, {"role": "Reviewed", "name": ""}, {"role": "Approved", "name": ""}],
    }


def _fixes_txt(h: dict) -> str:
    parts = [f"{_e(f['action'])} ({f['k']:g}/{f['n']})" for f in h["fixes"][:2]]
    return "; ".join(parts) or "—"


def _e(x) -> str:
    return html.escape(str(x)) if x is not None else "—"


def render_html(b: dict) -> str:
    hz_rows = "".join(
        f"<tr><td>{_e(h['formation_label'])}</td><td class=m>{h['top_md_m']:,.0f}</td><td>{_e(h['label'])}</td>"
        + (f"<td class=m>{h['mean'] * 100:.0f}%</td><td class=m>{h['ci'][0] * 100:.0f}–{h['ci'][1] * 100:.0f}%</td>" if h["status"] == "ok"
           else "<td colspan=2><i>insufficient evidence</i></td>")
        + f"<td class=m>{h['n_eff']:.1f}</td><td>{_fixes_txt(h)}</td></tr>"
        for h in b["hazards"])
    mw_rows = "".join(f"<tr><td>{_e(r['label'])}</td><td class=m>{_e(r['lower_ppg'])}</td><td class=m>{_e(r['upper_ppg'])}</td><td>{_e(r['status'].replace('_', ' '))}</td></tr>" for r in b["mud_window"])
    col = "".join(f"<tr><td class=m>{t['top_md_m']:,.0f}</td><td>{_e(t['label'])}</td></tr>" for t in b["formations"])
    offs = "".join(f"<tr><td>{_e(o['name'])}</td><td class=m>{o['distance_m']:,}</td><td class=m>{o['sim']:.2f}</td><td>{'yes' if o['documented'] else 'no'}</td></tr>" for o in b["offsets"])
    les = "".join(f"<li>{_e(l['well'])} — {_e(l['od_in'])}\" shoe at {l['shoe_md_m']:,.0f} m in {_e(l['label'])}: {_e(l['cement_issues'][0]['text'][:200])}</li>" for l in b["casing_lessons"])
    aud = "".join(f"<li>{_e(a['well'])}: {_e(a['rule'])} ({_e(a['delta'])})</li>" for a in b["audit"])
    src = "".join(f"<li class=m>{_e(s)}</li>" for s in b["sources"])
    sig = "".join(f"<div class=sig><div class=line></div><b>{_e(s['role'])}</b><br>{_e(s['name']) if s['name'] else '&nbsp;'}</div>" for s in b["signatures"])
    return f"""<!doctype html><html><head><meta charset=utf-8><title>{_e(b['ref_no'])}</title><style>
@page {{ size: A4; margin: 18mm 16mm 20mm 16mm; @bottom-center {{ content: "{_e(b['disclaimer'])}  ·  Page " counter(page); font: 8pt 'IBM Plex Sans', sans-serif; color: #5E5A50; }} }}
body {{ font: 10pt 'IBM Plex Sans', Helvetica, sans-serif; color: #1B1A17; }}
.hair {{ height: 2px; background: linear-gradient(90deg,#FF9933 33%,#fff 33% 66%,#138808 66%); margin-bottom: 8px; }}
.hdr {{ display:flex; justify-content:space-between; border-bottom: 1px solid #1B1A17; padding-bottom:4px; }}
.ref {{ font-family: 'Courier Prime', Courier, monospace; }}
h1 {{ font-size: 13pt; margin: 10px 0 4px; }} h2 {{ font-size: 10.5pt; margin: 14px 0 4px; border-bottom: 1px solid #CFC8B8; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9pt; }} td, th {{ border-bottom: 1px solid #CFC8B8; padding: 3px 4px; text-align: left; vertical-align: top; }}
th {{ font-weight: 600; }} .m {{ font-family: 'IBM Plex Mono', Menlo, monospace; font-variant-numeric: tabular-nums; }}
.sigs {{ display:flex; gap: 18px; margin-top: 26px; }} .sig {{ flex:1; font-size: 9pt; }} .line {{ border-bottom: 1px solid #1B1A17; height: 34px; margin-bottom: 3px; }}
.note {{ color:#5E5A50; font-size: 8.5pt; }} ul {{ margin: 2px 0 0 16px; padding: 0; }}
</style></head><body><div class=hair></div>
<div class=hdr><div>Kupakosh · Prototype for Oil India Limited · SIH 2026</div><div class=ref>No. {_e(b['ref_no'])} &nbsp; Dated {_e(b['date'])}</div></div>
<h1>Subject: {_e(b['subject'])}</h1>
<div class=note>Distribution: {_e(', '.join(b['distribution']))}. Offset radius {b['inputs']['radius_m']:,.0f} m; {b['n_offsets']} wells in radius, {b['n_documented']} with reports.
{'Formation tops inferred from the nearest documented offsets.' if b['inputs']['tops_inferred'] else 'Formation tops as planned.'}</div>
<h2>1. Formation column (expected tops, m MD)</h2><table><tr><th>Top</th><th>Formation</th></tr>{col}</table>
<h2>2. Hazards per formation (recorded-problem rate in offsets, 80% range)</h2>
<table><tr><th>Formation</th><th>Top</th><th>Hazard</th><th>Rate</th><th>Range</th><th>n_eff</th><th>What worked before (worked/cases)</th></tr>{hz_rows or '<tr><td colspan=7>No recorded hazard in offset wells.</td></tr>'}</table>
<div class=note>Rates are of problems <i>recorded</i> in reports; absence of a record is not proof of absence.</div>
<h2>3. Mud-weight window (ppg, from offset LOT/FIT, losses, kicks)</h2>
<table><tr><th>Formation</th><th>Lower</th><th>Upper</th><th>Status</th></tr>{mw_rows or '<tr><td colspan=4>Insufficient evidence.</td></tr>'}</table>
<h2>4. Casing &amp; cement lessons</h2><ul>{les or '<li>None recorded in offsets.</li>'}</ul>
<h2>5. Open report conflicts in offset wells</h2><ul>{aud or '<li>None open.</li>'}</ul>
<h2>6. Offset wells</h2><table><tr><th>Well</th><th>Distance (m)</th><th>Similarity</th><th>Reports</th></tr>{offs}</table>
<h2>7. Sources</h2><ul style="font-size:8pt">{src or '<li>—</li>'}</ul>
<div class=sigs>{sig}</div>
<p class=note style="margin-top:14px"><b>{_e(b['disclaimer'])}</b> {_e(b['data_note'])}</p>
</body></html>"""


def render_pdf(b: dict) -> bytes:
    from weasyprint import HTML  # needs pango (brew install pango; DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib on macOS)
    return HTML(string=render_html(b)).write_pdf()
