import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
DB = Path(__file__).resolve().parents[2] / "data" / "kupakosh.db"


@pytest.fixture(scope="session")
def db_ready():
    if not DB.exists():
        pytest.skip("database not built — run `make bootstrap` first")
    return True
