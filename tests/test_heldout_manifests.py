"""Held-out pair folders are complete and only name known cause kinds."""
from pathlib import Path

import pytest
import yaml

HELD = Path(__file__).resolve().parents[1] / "benchmark" / "heldout"
KINDS = {"FILTER_DIFF", "JOIN_DIFF", "JOIN_TYPE_DIFF", "AGG_EXPR_DIFF", "DISTINCT_DIFF", "TIME_DIFF"}
DIRS = sorted(p for p in HELD.iterdir() if p.is_dir()) if HELD.exists() else []


@pytest.mark.parametrize("d", DIRS, ids=lambda p: p.name)
def test_pair_is_complete(d):
    for f in ("query_a.sql", "query_b.sql", "manifest.yaml"):
        assert (d / f).exists(), f
    m = yaml.safe_load((d / "manifest.yaml").read_text())
    assert m["id"] == d.name
    assert set(m["planted_causes"] or []) <= KINDS