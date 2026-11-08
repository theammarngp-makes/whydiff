"""Attribution tests: hand-computed toy games, then every benchmark pair."""
from pathlib import Path

import pytest

from test_evaluator import con  # noqa: F401  (reuse the synthetic database fixture)
from whydiff.attribution import (attribute, sequential_attribution,
                                 shapley_exact, shapley_monte_carlo)
from whydiff.evaluator import Evaluator

PAIRS = sorted((Path(__file__).resolve().parents[1] / "benchmark" / "pairs").glob("P*"))

# Toy game worked out by hand: v(empty)=0, v({A})=10, v({B})=20, v({A,B})=50.
# phi_A = 1/2*(10-0) + 1/2*(50-20) = 20 ; phi_B = 1/2*(20-0) + 1/2*(50-10) = 30
TOY = {frozenset(): 0, frozenset("A"): 10, frozenset("B"): 20, frozenset("AB"): 50}


def toy(s):
    return TOY[frozenset(s)]


def test_toy_exact_matches_hand_calculation():
    phi = shapley_exact(["A", "B"], toy)
    assert phi["A"] == pytest.approx(20.0)
    assert phi["B"] == pytest.approx(30.0)
    assert sum(phi.values()) == pytest.approx(toy("AB") - toy(""))


def test_additive_game_gives_each_player_its_own_weight():
    w = {"x": 3.0, "y": 5.0, "z": 7.0}
    phi = shapley_exact(list(w), lambda s: sum(w[p] for p in s))
    assert phi == pytest.approx(w)


def test_symmetric_game_splits_equally():
    phi = shapley_exact(["a", "b", "c"], lambda s: len(s) ** 2)  # total 9, three equal players
    assert all(x == pytest.approx(3.0) for x in phi.values())


def test_sequential_depends_on_order_but_shapley_does_not():
    assert sequential_attribution(["A", "B"], toy) == {"A": 10, "B": 40}
    assert sequential_attribution(["B", "A"], toy) == {"B": 20, "A": 30}


def test_monte_carlo_total_is_exact_and_values_are_close():
    phi = shapley_monte_carlo(["A", "B"], toy, n_perm=2000, seed=1)
    assert sum(phi.values()) == pytest.approx(50.0)
    assert phi["A"] == pytest.approx(20.0, abs=1.5)


@pytest.mark.parametrize("d", PAIRS, ids=[p.name for p in PAIRS])
def test_identity_holds_for_every_pair(con, d):  # noqa: F811
    ev = Evaluator(con, (d / "query_a.sql").read_text(), (d / "query_b.sql").read_text())
    r = attribute(ev)
    total = sum(c["effect"] for c in r["causes"]) + r["residual"]
    assert total == pytest.approx(r["gap"], rel=1e-9, abs=1e-6)
    assert r["identity_ok"]


def test_single_cause_pair_gets_the_whole_gap(con):  # noqa: F811
    d = {p.name: p for p in PAIRS}["P01"]
    r = attribute(Evaluator(con, (d / "query_a.sql").read_text(), (d / "query_b.sql").read_text()))
    assert r["causes"][0]["effect"] == pytest.approx(r["gap"])
    assert r["residual"] == pytest.approx(0.0, abs=1e-6)