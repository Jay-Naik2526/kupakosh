"""Canonical well IDs (SPEC.md §6).

Volve/Sodir spell the same wellbore several ways: '15/9-F-5', 'NO 15/9-F-5',
'15_9-F-5', '15$47$9-F-5'. canonical() maps them all to '15/9-F-5'.
FORGE wells: '16A(78)-32', '16A 78-32', 'FORGE 16A (78)-32' -> '16A(78)-32'.
"""
from __future__ import annotations

import re

_FORGE = re.compile(r"(?:utah\s+)?(?:forge\s+)?(\d+[A-Z]?)\s*\(?\s*(\d+)\s*\)?\s*-\s*(\d+)", re.I)


def canonical(name: str) -> str:
    s = (name or "").strip()
    s = re.sub(r"^\s*NO\s+", "", s, flags=re.I)
    s = s.replace("$47$", "/")
    s = re.sub(r"\s+", " ", s)
    m = re.match(r"^(\d{1,4})[_/ ](\d{1,2})\s*-\s*(.+)$", s)
    if m:
        rest = re.sub(r"\s*-\s*", "-", m.group(3).strip())
        rest = re.sub(r"\s+", " ", rest)
        return f"{m.group(1)}/{m.group(2)}-{rest}".upper()
    m = _FORGE.search(s)
    if m and ("forge" in s.lower() or "(" in s or re.match(r"^\d+[A-Z]?\s*\(?\d+\)?-\d+$", s)):
        return f"{m.group(1).upper()}({m.group(2)})-{m.group(3)}"
    return s.upper()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", canonical(name).lower()).strip("-")
