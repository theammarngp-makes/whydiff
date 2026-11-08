from types import SimpleNamespace as NS

import pytest

from whydiff.benchmark import PLANTED, order_spread_pct, score_causes


def cause(cid, *kinds):
    return NS(id=cid, members=[NS(kind=k) for k in kinds])


def test_planted_table_covers_all_16_pairs():
    assert sorted(PLANTED) == [f"P{i:02d}" for i in range(1, 17)]


def test_combined_cause_matches_any_member_kind():
    causes = [cause("c1", "JOIN_DIFF", "AGG_EXPR_DIFF"), cause("c2", "FILTER_DIFF")]
    assert score_causes(["JOIN_DIFF", "FILTER_DIFF"], causes) == (2, 1.0, 1.0)


def test_extra_reported_cause_lowers_precision():
    causes = [cause("c1", "FILTER_DIFF"), cause("c2", "TIME_DIFF")]
    assert score_causes(["FILTER_DIFF"], causes) == (1, 1.0, 0.5)


def test_missed_cause_lowers_recall():
    assert score_causes(["FILTER_DIFF", "TIME_DIFF"], [cause("c1", "FILTER_DIFF")]) == (1, 0.5, 1.0)


def test_clean_pair_has_no_ratios():
    assert score_causes([], []) == (0, None, None)


def fake_ev(values):
    ids = ["c1", "c2"]
    return NS(causes=[cause(i, "X") for i in ids], v=lambda s: values[frozenset(s)])


def test_order_spread_zero_when_effects_are_additive():
    ev = fake_ev({frozenset(): 0, frozenset({"c1"}): 10, frozenset({"c2"}): 20,
                  frozenset({"c1", "c2"}): 30})
    assert order_spread_pct(ev, {"c1": 10, "c2": 20}) == pytest.approx(0.0)


def test_order_spread_positive_when_causes_interact():
    ev = fake_ev({frozenset(): 0, frozenset({"c1"}): 10, frozenset({"c2"}): 10,
                  frozenset({"c1", "c2"}): 30})
    # forward gives c1=10, c2=20; reverse gives c2=10, c1=20; gross effect is 30
    assert order_spread_pct(ev, {"c1": 15, "c2": 15}) == pytest.approx(100 * 10 / 30)


def test_order_spread_none_for_single_cause():
    ev = NS(causes=[cause("c1", "X")], v=lambda s: 0)
    assert order_spread_pct(ev, {"c1": 5}) is None

def test_combined_cause_can_absorb_several_planted_kinds():
    causes = [cause("c1", "AGG_EXPR_DIFF", "JOIN_DIFF")]
    assert score_causes(["AGG_EXPR_DIFF", "JOIN_DIFF"], causes) == (2, 1.0, 1.0)


def test_each_member_difference_is_used_once():
    causes = [cause("c1", "FILTER_DIFF")]
    assert score_causes(["FILTER_DIFF", "FILTER_DIFF"], causes) == (1, 0.5, 1.0)    