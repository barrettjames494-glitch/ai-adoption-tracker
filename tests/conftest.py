import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tracker import sample, transform  # noqa: E402

TOOLS = [
    {"name": "Alpha", "repo": "org/alpha", "category": "Agents"},
    {"name": "Beta", "repo": "org/beta", "category": "SDK"},
    {"name": "Gamma", "repo": "org/gamma", "category": "Agents"},
]
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def raw():
    return sample.make_raw(TOOLS, seed=1, now=NOW)


@pytest.fixture
def tables(raw):
    return transform.build_tables(raw, snapshot_at=NOW)
