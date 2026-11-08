import pytest

from test_diagnostics import mini_con, q  # noqa: F401
from whydiff.report import build_report, is_offsetting, summarize, waterfall_steps


def res(a, b, causes, residual=0.0):
    gap = b - a
    return {"result_a": a, "result_b": b, "gap": gap, "residual": residual,
            "causes": [{"id": f"c{i}", "kind": k, "description": k, "effect": e,
                        "share_pct": 100 * e / gap if gap else None}
                       for i, (k, e) in enumerate(causes, 1)]}


def test_normal_summary_gives_shares():
    s = summarize(res(200, 100, [("JOIN_DIFF", -60), ("FILTER_DIFF", -40)]))
    assert "60%" in s and "40%" in s and "no unexplained residual" in s


def test_same_value_no_causes():
    assert "same value" in summarize(res(5, 5, []))


def test_offsetting_is_flagged_and_explained():
    r = res(100, 100.5, [("AGG_EXPR_DIFF", 500), ("TIME_DIFF", -499.5)])
    assert is_offsetting(r)
    assert "cancel out" in summarize(r)


def test_waterfall_steps_order_and_residual():
    steps = waterfall_steps(res(10, 20, [("X", 8)], residual=2.0))
    assert [s["label"] for s in steps] == ["Query A", "c1: X", "Unexplained", "Query B"]
    assert [s["measure"] for s in steps] == ["absolute", "relative", "relative", "total"]


def test_build_report_end_to_end(mini_con):  # noqa: F811
    sql_b = ("SELECT SUM(items.price) AS revenue FROM orders "
             "JOIN items ON items.order_id = orders.order_id")
    rep = build_report(mini_con, q("pay"), sql_b)
    r = rep["attribution"]
    assert r["gap"] == pytest.approx(-30)
    assert [c["kind"] for c in r["causes"]] == ["JOIN_DIFF"]
    assert abs(r["residual"]) < 1e-9
    assert rep["trail_a"][2]["fan_out"] is True and len(rep["trail_b"]) == 2