"""Config loader: all thresholds come from config/*.yaml (SPEC.md §0.6)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
EVAL_DIR = DATA_DIR / "eval"
WIKI_DIR = Path(os.environ.get("WIKI_REPO_PATH", ROOT / "wiki"))
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'kupakosh.db'}")


@lru_cache
def cfg() -> dict:
    return yaml.safe_load((CONFIG_DIR / "default.yaml").read_text())


@lru_cache
def taxonomy() -> dict:
    return yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())
