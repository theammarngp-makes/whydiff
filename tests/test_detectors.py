"""Detector acceptance test: found differences must equal the planted causes."""
from pathlib import Path

import pytest
import yaml

from whydiff.detectors import diff_profiles
from whydiff.profile import UnsupportedConstruct, build_profile

PAIRS = sorted((Path(__file__).resolve().parents[1] / "benchmark" / "pairs").glob("P*"))


@pytest.mark.parametrize("d", PAIRS, ids=[p.name for p in PAIRS])
def test_pair(d):
    m = yaml.safe_load((d / "manifest.yaml").read_text())
    diffs = diff_profiles(build_profile((d / "query_a.sql").read_text()),
                          build_profile((d / "query_b.sql").read_text()))
    assert sorted(x.kind for x in diffs) == sorted(m["planted_causes"])


def test_unsupported_window_function():
    with pytest.raises(UnsupportedConstruct):
        build_profile("SELECT SUM(x) OVER (ORDER BY y) FROM t")