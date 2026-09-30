"""Negative result kept on record: "drilling déjà vu" (match the live sensor pattern to the hour before past problems).

Test: for every trusted, timed problem on a well with recorded sensor data (Utah FORGE 16A and 16B), take the
sensor signature of the hour before it (level, trend and spread of torque, standpipe pressure, hookload, flow,
pit volume and ROP against the previous 6 hours). Score every minute of that well by its best cosine match to the
OTHER well's pre-problem signatures, and ask where the real pre-problem minute ranks among all of them.
Chance is the 50th percentile. Measured: well below chance, so the idea is NOT used in the product. The likely
reason: problem times come from daily-report lines that span 0.5–10 hours, far too coarse for minute-level
sensor matching. Kept so the Accuracy page shows what was tried and did not work.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import EvalResult

CH = ["torque", "spp", "hookload", "flow_in", "pit_vol", "rop"]


def _features(db: Session, well_id: int):
    import pandas as pd
    df = pd.read_sql(f"select t,{','.join(CH)} from realtime_sample where well_id = {int(well_id)} order by t", db.bind, parse_dates=["t"])
    if df.empty:
        return None
    s = df.set_index("t").resample("1min").median()
    out = {}
    for c in CH:
        x = s[c]
        base_med = x.rolling("360min", min_periods=30).median().shift(60)
        base_mad = (x - base_med).abs().rolling("360min", min_periods=30).median().shift(60) + 1e-6
        w_med = x.rolling("60min", min_periods=20).median()
        first, last = x.rolling("15min", min_periods=5).median().shift(45), x.rolling("15min", min_periods=5).median()
        out[c + "_lvl"] = ((w_med - base_med) / base_mad).clip(-20, 20)
        out[c + "_slope"] = ((last - first) / base_mad).clip(-20, 20)
        out[c + "_var"] = np.log1p((x - w_med).abs().rolling("60min", min_periods=20).median() / base_mad).clip(0, 5)
    return pd.DataFrame(out).dropna()


def run(db: Session) -> list[EvalResult]:
    from sqlalchemy import select
    from app.db.models import Event, RealtimeSample
    wells = [w for (w,) in db.execute(select(RealtimeSample.well_id).distinct())]
    if len(wells) < 2:
        return []
    F = {w: _features(db, w) for w in wells}
    ev = db.execute(select(Event.id, Event.well_id, Event.t).where(Event.needs_review.is_(False), Event.well_id.in_(wells), Event.t.is_not(None))).all()
    Z = {w: ((f - f.mean()) / (f.std() + 1e-6), f.mean(), f.std() + 1e-6) for w, f in F.items() if f is not None}

    def sig(w, t):
        f = F[w].loc[:t]
        if f.empty or (t - f.index[-1]).total_seconds() > 1800:
            return None
        return np.array(((f.iloc[-1] - Z[w][1]) / Z[w][2]).values, dtype=float)

    pct = []
    for _, w, t in ev:
        q = sig(w, t)
        lib = [s for _, w2, t2 in ev if w2 != w and (s := sig(w2, t2)) is not None]
        if q is None or not lib:
            continue
        L = np.array(lib)
        L /= np.linalg.norm(L, axis=1, keepdims=True)
        zf = Z[w][0].values
        zf = zf / np.linalg.norm(zf, axis=1, keepdims=True)
        best = (zf @ L.T).max(1)
        pct.append(float((best < ((q / np.linalg.norm(q)) @ L.T).max()).mean()))
    if not pct:
        return []
    p = np.array(pct)
    return [EvalResult(name="dejavu", metric="pre-problem hour rank (percentile, chance 0.5)", value=float(np.median(p)), n=len(p),
                       notes=(f"NOT USED IN THE PRODUCT: no skill measured. Sensor signature of the hour before each timed problem on FORGE "
                              f"16A/16B, matched to the other well's; median percentile {np.median(p):.2f} (chance 0.50), "
                              f"{int((p >= 0.9).sum())} of {len(p)} in the top 10%. Problem times come from 0.5–10 h report lines, "
                              "too coarse for minute-level matching."))]
