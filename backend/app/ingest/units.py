from __future__ import annotations

from app.config import cfg


def ft_to_m(x: float | None) -> float | None:
    return None if x is None else x * cfg()["conversions"]["ft_to_m"]


def sg_to_ppg(x: float | None) -> float | None:
    return None if x is None else x * cfg()["conversions"]["sg_to_ppg"]


def m3_to_bbl(x: float | None) -> float | None:
    return None if x is None else x * cfg()["conversions"]["m3_to_bbl"]


def to_float(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", ".") if isinstance(v, str) and v.count(",") == 1 and "." not in v else str(v).strip()
    if s in ("", "-", "nan", "NaN", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None
