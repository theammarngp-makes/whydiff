"""Evaluator tests on a small synthetic database (no Olist data needed)."""
from pathlib import Path

import duckdb
import pytest

from whydiff.evaluator import Evaluator

PAIRS = sorted((Path(__file__).resolve().parents[1] / "benchmark" / "pairs").glob("P*"))


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute("CREATE TABLE base AS SELECT i, 'o' || i AS order_id FROM range(1, 1201) t(i)")
    c.execute("""CREATE TABLE orders AS SELECT order_id, 'c' || i AS customer_id,
        CASE WHEN i % 9 = 0 THEN 'canceled' WHEN i % 11 = 0 THEN 'shipped' ELSE 'delivered' END
          AS order_status,
        TIMESTAMP '2017-10-15 00:00:00' + i * INTERVAL 1 HOUR AS order_purchase_timestamp
        FROM base""")
    c.execute("""CREATE TABLE order_items AS SELECT b.order_id, k AS order_item_id,
        10.0 + (b.i % 17) AS price, 2.5 + (b.i % 5) AS freight_value
        FROM base b, range(1, 4) t(k) WHERE (b.i + k) % 4 <> 0""")
    c.execute("""CREATE TABLE order_payments AS SELECT b.order_id, k AS payment_sequential,
        20.0 + (b.i % 13) AS payment_value
        FROM base b, range(1, 3) t(k) WHERE b.i % 6 <> 0 AND NOT (k = 2 AND b.i % 3 = 0)""")
    c.execute("""CREATE TABLE order_reviews AS SELECT 'r' || b.i || '_' || k AS review_id,
        b.order_id, 5 AS review_score
        FROM base b, range(1, 3) t(k) WHERE b.i % 5 <> 0 AND NOT (k = 2 AND b.i % 4 <> 0)""")
    c.execute("""CREATE TABLE customers AS SELECT 'c' || i AS customer_id,
        'u' || (i % 500) AS customer_unique_id FROM base""")
    return c


def _ev(con, d):
    return Evaluator(con, (d / "query_a.sql").read_text(), (d / "query_b.sql").read_text())


@pytest.mark.parametrize("d", PAIRS, ids=[p.name for p in PAIRS])
def test_all_patches_reproduce_b(con, d):
    ev = _ev(con, d)
    assert ev.v(ev.all_ids) == pytest.approx(ev.result_b, rel=1e-9, abs=1e-9)


def test_bundling_counts(con):
    by_id = {p.name: p for p in PAIRS}
    assert len(_ev(con, by_id["P04"]).causes) == 1       # source-table switch is one cause
    assert len(_ev(con, by_id["P11"]).causes) == 3       # independent causes stay separate
    assert len(_ev(con, by_id["P14"]).causes) == 0


def test_cache_counts_each_subset_once(con):
    ev = _ev(con, {p.name: p for p in PAIRS}["P11"])
    for _ in range(3):
        ev.v(frozenset({"c1"}))
    assert ev.n_evaluations == 2                          # empty set + {c1}