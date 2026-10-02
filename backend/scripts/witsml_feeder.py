"""Stand-in for a rig's real-time server (eRTMAC or any WITSML store): post drilling data to Kupakosh as it "happens".

It reads RECORDED sensor rows of a well from the database and posts them in real time as WITSML 1.4.1 log documents
(or WITS0 records) to POST /api/live/{well_id}/witsml, exactly as an external sender would: over HTTP, with the feed
token. Open the Command page, choose "Live feed", and watch the same alerts arrive through the live path.

    python -m scripts.witsml_feeder --well 16B --start-md 1500 --speed 120
    python -m scripts.witsml_feeder --well 16B --format wits0 --url https://kupakosh.duckdns.org --token "$KK_FEED_TOKEN"

The token is KK_FEED_TOKEN on the server, or data/processed/feed_token.txt (created on first use). The feed is
labelled with --source so viewers can see it is recorded data, not a live rig.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import timedelta, timezone

from sqlalchemy import select

from app.db.models import RealtimeSample, Well
from app.db.session import SessionLocal
from app.engines.livefeed import feed_token
from app.ingest.witsml_stream import to_witsml_log

WITS0_CODES = {"bit_md_m": "0108", "md_m": "0110", "rop": "0113", "hookload": "0114", "wob": "0116", "torque": "0118",
               "rpm": "0120", "spp": "0121", "pit_vol": "0126", "flow_in": "0130"}


def to_wits0(rows: list[dict]) -> str:
    """Imperial-unit WITS0 records (internal units are imperial-compatible except depth and ROP, converted back)."""
    out = []
    for r in rows:
        lines = ["&&", f"0105{r['t']:%y%m%d}", f"0106{r['t']:%H%M%S}"]
        for k, code in WITS0_CODES.items():
            v = r.get(k)
            if v is None:
                continue
            if k in ("md_m", "bit_md_m", "rop"):
                v = v / 0.3048
            lines.append(f"{code}{v:.3f}")
        lines.append("!!")
        out.append("\n".join(lines))
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--well", required=True, help="well name (start of canonical name, e.g. 16B) or id")
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--token", default=None)
    ap.add_argument("--format", choices=["witsml", "wits0"], default="witsml")
    ap.add_argument("--speed", type=float, default=120, help="recorded seconds sent per real second")
    ap.add_argument("--start-md", type=float, default=None)
    ap.add_argument("--every", type=float, default=1.0, help="seconds between posts")
    ap.add_argument("--source", default="witsml_feeder.py: recorded Utah FORGE rig data re-sent over HTTP - not a live rig")
    a = ap.parse_args()
    with SessionLocal() as db:
        w = db.get(Well, int(a.well)) if a.well.isdigit() else db.scalars(select(Well).where(Well.canonical_name.like(f"%{a.well}%"))
                                                                          .join(RealtimeSample, RealtimeSample.well_id == Well.id).limit(1)).first()
        if not w:
            sys.exit(f"no well with recorded sensor data matches {a.well!r}")
        rows = [{"t": r.t if r.t.tzinfo else r.t.replace(tzinfo=timezone.utc),
                 **{k: getattr(r, k) for k in ("md_m", "bit_md_m", "rop", "wob", "rpm", "torque", "spp", "flow_in", "pit_vol", "hookload")}}
                for r in db.scalars(select(RealtimeSample).where(RealtimeSample.well_id == w.id).order_by(RealtimeSample.t))]
        name, wid = w.canonical_name, w.id
    token = a.token or feed_token()
    i = next((k for k, r in enumerate(rows) if (r["md_m"] or 0) >= a.start_md), 0) if a.start_md is not None else 0
    path = f"/api/live/{wid}/witsml" if a.format == "witsml" else f"/api/live/{wid}/wits0?units=imperial"
    print(f"sending {name} (id {wid}) from row {i} of {len(rows)} as {a.format} to {a.url}{path}")
    sim_t = rows[i]["t"]
    while i < len(rows):
        sim_t += timedelta(seconds=a.speed * a.every)
        chunk = []
        while i < len(rows) and rows[i]["t"] <= sim_t:
            chunk.append(rows[i])
            i += 1
        if chunk:
            body = (to_witsml_log(name, chunk) if a.format == "witsml" else to_wits0(chunk)).encode()
            req = urllib.request.Request(a.url + path, data=body, method="POST", headers={
                "Authorization": f"Bearer {token}", "X-Feed-Source": a.source,
                "Content-Type": "application/xml" if a.format == "witsml" else "text/plain"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    ack = json.load(r)
                print(f"{chunk[-1]['t']:%Y-%m-%d %H:%M:%S}  +{ack['accepted']:4d} rows  bit {ack['bit_md_m'] or 0:7.1f} m  viewers {ack['viewers']}")
            except urllib.error.HTTPError as e:
                sys.exit(f"server refused: {e.code} {e.read().decode()[:300]}")
        time.sleep(a.every)
    print("done")


if __name__ == "__main__":
    main()
