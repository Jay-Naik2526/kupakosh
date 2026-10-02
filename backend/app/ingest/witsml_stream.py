"""Parse live rig data the way a rig system sends it, into the same sample rows the replay uses.

Two formats, both industry standards used by real-time systems such as Oil India's eRTMAC:
  * WITSML 1.4.1 `log` objects (XML): <logCurveInfo> mnemonics and units + <logData> rows of comma-separated values.
  * WITS Level 0 (ASCII): records between "&&" and "!!", one "IIIIvalue" line per item (record 01, time-based drilling).

Mnemonics, WITS item codes and unit conversions live in config/default.yaml -> livefeed. Values in an unknown unit
are dropped (reported in `skipped`), never guessed. Internal units match the replay: depth m, torque kft.lbf,
SPP psi, flow gpm, pit volume bbl, hookload / WOB klbf.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from app.config import cfg

CHANNELS = ("md_m", "bit_md_m", "rop", "wob", "rpm", "torque", "spp", "flow_in", "pit_vol", "hookload")


class FeedError(ValueError):
    """The posted document cannot be read; the message says why (shown to the sender)."""


def _conv(channel: str, value: float, unit: str | None, skipped: set) -> float | None:
    if channel == "time":
        return value
    units = cfg()["livefeed"]["units"]
    u = (unit or "").strip().lower().replace(" ", "") if unit else ""
    u = {"meters": "m", "metres": "m", "feet": "ft", "ft-lbf": "ft.lbf", "kft-lbf": "kft.lbf", "kft_lb": "kft.lbf", "ft_lbs": "ft.lbf",
         "knm": "kn.m", "nm": "n.m", "gpm": "gpm", "galus/min": "gal/min", "m3": "m3", "1000kgf": "1000 kgf", "klb": "klbf"}.get(u, u)
    if u not in units:
        skipped.add(f"{channel} [{unit or 'no unit'}]")
        return None
    return value * float(units[u][1])


def _parse_time(s: str) -> datetime | None:
    s = s.strip()
    if not s:
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_witsml_log(xml: bytes | str) -> dict:
    """WITSML 1.4.1 <logs><log>…</log></logs> -> {"well": name, "samples": [...], "skipped": [...], "channels": [...]}.
    Each sample has `t` (ISO time, or None for depth-indexed logs) and the internal channels found."""
    raw = xml.encode() if isinstance(xml, str) else xml
    head = raw[:4000].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:  # no DTDs / entities from the network
        raise FeedError("DOCTYPE / ENTITY declarations are not accepted")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise FeedError(f"not well-formed XML: {e}") from None
    logs = [el for el in root.iter() if _local(el.tag) == "log"]
    if not logs:
        raise FeedError("no WITSML <log> element found")
    lookup = {}
    for ch, names in cfg()["livefeed"]["witsml_mnemonics"].items():
        for n in names:
            lookup.setdefault(n.upper(), ch)
    samples, skipped, found, well = [], set(), set(), None
    for log in logs:
        well = well or next((c.text for c in log if _local(c.tag) == "nameWell" and c.text), None)
        units = {}
        for info in (c for c in log if _local(c.tag) == "logCurveInfo"):
            mn = next((c.text for c in info if _local(c.tag) == "mnemonic"), None)
            un = next((c.text for c in info if _local(c.tag) == "unit"), None)
            if mn:
                units[mn.strip().upper()] = un
        data = next((c for c in log if _local(c.tag) == "logData"), None)
        if data is None:
            continue
        mlist = next((c.text for c in data if _local(c.tag) == "mnemonicList"), None)
        if not mlist:
            raise FeedError("<logData> has no <mnemonicList>")
        mnems = [m.strip().upper() for m in mlist.split(",")]
        ulist = next((c.text for c in data if _local(c.tag) == "unitList"), None)
        row_units = [u.strip() for u in ulist.split(",")] if ulist else [units.get(m) for m in mnems]
        cols = [(i, lookup.get(m), row_units[i] if i < len(row_units) else units.get(m)) for i, m in enumerate(mnems)]
        for m, (_, ch, _) in zip(mnems, cols):
            if ch is None:
                skipped.add(m)
        for d in (c for c in data if _local(c.tag) == "data"):
            vals = (d.text or "").split(",")
            s: dict = {"t": None}
            for i, ch, unit in cols:
                if ch is None or i >= len(vals) or vals[i].strip() in ("", "-999.25", "-9999"):
                    continue
                if ch == "time":
                    t = _parse_time(vals[i])
                    s["t"] = t.isoformat() if t else None
                    continue
                try:
                    v = float(vals[i])
                except ValueError:
                    continue
                v = _conv(ch, v, unit, skipped)
                if v is not None and ch not in s:
                    s[ch] = v
                    found.add(ch)
            if len(s) > 1:
                samples.append(s)
    return _finish(well, samples, skipped, found)


def parse_wits0(text: str, units: str = "metric") -> dict:
    """WITS Level 0 records. Only record 01 (time-based drilling) items configured in livefeed.wits0_items are read;
    date (0105, YYMMDD) and time (0106, HHMMSS) give the sample time when present."""
    c = cfg()["livefeed"]
    if units not in c["wits0_units"]:
        raise FeedError(f"units must be one of {sorted(c['wits0_units'])}")
    unit_of = c["wits0_units"][units]
    items = c["wits0_items"]
    samples, skipped, found = [], set(), set()
    blocks = re.findall(r"&&(.*?)!!", text, flags=re.S)
    if not blocks:
        raise FeedError("no WITS0 record found (expected lines between && and !!)")
    for b in blocks:
        s: dict = {"t": None}
        date = tm = None
        for line in b.splitlines():
            line = line.strip()
            m = re.match(r"^(\d{4})(.*)$", line)
            if not m:
                continue
            code, val = m.groups()
            if code == "0105":
                date = val.strip()
            elif code == "0106":
                tm = val.strip()
            elif code in items:
                try:
                    v = float(val)
                except ValueError:
                    continue
                ch = items[code]
                v = _conv(ch, v, unit_of.get(ch), skipped)
                if v is not None:
                    s[ch] = v
                    found.add(ch)
            elif code.startswith("01"):
                skipped.add(code)
        if date and tm and len(date) == 6 and len(tm) >= 6:
            try:
                s["t"] = datetime.strptime(date + tm[:6], "%y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
        if len(s) > 1:
            samples.append(s)
    return _finish(None, samples, skipped, found)


def _finish(well, samples, skipped, found) -> dict:
    if len(samples) > cfg()["livefeed"]["max_samples_per_post"]:
        raise FeedError(f"too many rows in one post ({len(samples)}); send smaller batches")
    for s in samples:  # the hole depth is what the look-ahead needs; fall back to bit depth when only that is sent
        if s.get("md_m") is None and s.get("bit_md_m") is not None:
            s["md_m"] = s["bit_md_m"]
    return {"well": well, "samples": samples, "channels": sorted(found), "skipped": sorted(skipped)}


def to_witsml_log(well: str, rows: list[dict], uid: str = "kupakosh-demo") -> str:
    """Write rows (internal units, `t` as datetime) as a WITSML 1.4.1 log document. Used by the demo feeder, so the
    demo goes through exactly the parser a real eRTMAC / WITSML server feed would."""
    mn = [("TIME", "s", "t"), ("DEPT", "m", "md_m"), ("DBTM", "m", "bit_md_m"), ("ROPA", "m/h", "rop"), ("SWOB", "klbf", "wob"),
          ("RPMA", "rpm", "rpm"), ("TQA", "kft.lbf", "torque"), ("SPPA", "psi", "spp"), ("MFIA", "gal/min", "flow_in"),
          ("TVA", "bbl", "pit_vol"), ("HKLA", "klbf", "hookload")]

    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, datetime):
            return v.isoformat()
        return f"{v:.4f}".rstrip("0").rstrip(".")
    curves = "".join(f'<logCurveInfo uid="{m}"><mnemonic>{m}</mnemonic><unit>{u}</unit></logCurveInfo>' for m, u, _ in mn)
    data = "".join(f"<data>{','.join(fmt(r.get(k)) for _, _, k in mn)}</data>" for r in rows)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<logs xmlns="http://www.witsml.org/schemas/1series" version="1.4.1.1">'
            f'<log uidWell="{uid}" uidWellbore="{uid}" uid="{uid}-log"><nameWell>{well}</nameWell><nameWellbore>{well}</nameWellbore>'
            f'<name>Realtime drilling</name><indexType>date time</indexType><indexCurve>TIME</indexCurve>{curves}'
            f'<logData><mnemonicList>{",".join(m for m, _, _ in mn)}</mnemonicList><unitList>{",".join(u for _, u, _ in mn)}</unitList>'
            f'{data}</logData></log></logs>')
