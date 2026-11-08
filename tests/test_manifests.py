from pathlib import Path

from whydiff.benchmark import PLANTED, load_planted

PAIRS = Path(__file__).resolve().parent.parent / "benchmark" / "pairs"


def test_manifests_agree_with_design_table():
    for pid, kinds in PLANTED.items():
        assert sorted(load_planted(PAIRS / pid)) == sorted(kinds), pid