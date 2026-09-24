"""Minimum-curvature trajectory calculation (used to verify vendor TVD and for wells without TVD)."""
from __future__ import annotations

import math


def min_curvature(stations: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    """stations: [(md, inc_deg, azi_deg), ...] sorted by md, first at surface.
    returns [(tvd, north, east), ...] in the same length unit as md."""
    out = [(0.0, 0.0, 0.0)]
    tvd = n = e = 0.0
    for (md1, i1, a1), (md2, i2, a2) in zip(stations, stations[1:]):
        i1r, i2r, a1r, a2r = map(math.radians, (i1, i2, a1, a2))
        dmd = md2 - md1
        cos_dl = math.cos(i2r - i1r) - math.sin(i1r) * math.sin(i2r) * (1 - math.cos(a2r - a1r))
        dl = math.acos(max(-1.0, min(1.0, cos_dl)))
        rf = 1.0 if dl < 1e-9 else (2 / dl) * math.tan(dl / 2)
        tvd += dmd / 2 * (math.cos(i1r) + math.cos(i2r)) * rf
        n += dmd / 2 * (math.sin(i1r) * math.cos(a1r) + math.sin(i2r) * math.cos(a2r)) * rf
        e += dmd / 2 * (math.sin(i1r) * math.sin(a1r) + math.sin(i2r) * math.sin(a2r)) * rf
        out.append((tvd, n, e))
    return out
