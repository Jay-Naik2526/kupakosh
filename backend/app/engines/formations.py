"""Formation lookup by depth, and display-name helpers."""
from __future__ import annotations

import re
from bisect import bisect_right
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FormationTop


def pretty(name: str | None) -> str | None:
    """'BLODØKS FM' -> 'Blodøks Fm', 'NORDLAND GP' -> 'Nordland Gp'."""
    if not name:
        return name
    return " ".join(w.capitalize() if not re.match(r"^[IVX]+$", w) else w for w in name.split())


class TopIndex:
    """In-memory index of formation tops per well (FORMATION level preferred, GROUP fallback)."""

    def __init__(self, db: Session, well_ids: list[int] | None = None):
        q = select(FormationTop)
        if well_ids is not None:
            q = q.where(FormationTop.well_id.in_(well_ids))
        self.by_well: dict[int, dict[str, list[FormationTop]]] = defaultdict(lambda: {"FORMATION": [], "GROUP": []})
        for t in db.scalars(q):
            if t.top_md_m is None:
                continue
            self.by_well[t.well_id].setdefault(t.level or "FORMATION", []).append(t)
        for lv in self.by_well.values():
            for lst in lv.values():
                lst.sort(key=lambda t: t.top_md_m)

    def at(self, well_id: int, md: float | None) -> str | None:
        if md is None or well_id not in self.by_well:
            return None
        for level in ("FORMATION", "GROUP"):
            lst = self.by_well[well_id].get(level) or []
            i = bisect_right([t.top_md_m for t in lst], md) - 1
            if i >= 0:
                t = lst[i]
                if t.base_md_m is None or md <= t.base_md_m:
                    return t.formation
        return None

    def sequence(self, well_id: int, level: str = "FORMATION") -> list[str]:
        return [t.formation for t in self.by_well.get(well_id, {}).get(level, [])]

    def tops(self, well_id: int) -> list[FormationTop]:
        lv = self.by_well.get(well_id)
        if not lv:
            return []
        return sorted(lv.get("FORMATION", []) + lv.get("GROUP", []), key=lambda t: (t.top_md_m, t.level != "GROUP"))

    def penetrated(self, well_id: int) -> set[str]:
        lv = self.by_well.get(well_id)
        if not lv:
            return set()
        # only stratigraphic units: MEMBER (NLOG) and LITHOLOGY (FORCE 2020 log-derived rock types) are finer
        # descriptions and would inflate well-to-well similarity if they counted as formations
        return {t.formation for level in ("FORMATION", "GROUP") for t in lv.get(level, [])}
