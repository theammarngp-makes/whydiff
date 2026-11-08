import duckdb
import pytest

from whydiff.diagnostics import row_count_trail


def q(pay_table):
    return ("SELECT SUM(items.price) AS revenue FROM orders "
            "JOIN items ON items.order_id = orders.order_id "
            f"JOIN {pay_table} ON {pay_table}.order_id = orders.order_id")


@pytest.fixture
def mini_con():
    c = duckdb.connect()
    c.execute("CREATE TABLE orders AS SELECT * FROM (VALUES (1),(2),(3)) t(order_id)")
    c.execute("CREATE TABLE items AS SELECT * FROM "
              "(VALUES (1,10),(1,20),(2,30),(3,40)) t(order_id, price)")
    c.execute("CREATE TABLE pay AS SELECT * FROM "
              "(VALUES (1,5),(1,6),(2,6),(3,7)) t(order_id, amount)")
    c.execute("CREATE TABLE pay1 AS SELECT * FROM (VALUES (1,5),(2,6),(3,7)) t(order_id, amount)")
    return c


def test_trail_counts_rows_after_each_join(mini_con):
    steps = row_count_trail(mini_con, q("pay"))
    assert [s.rows_after for s in steps] == [3, 4, 6]
    assert steps[0].join_kind == "BASE"


def test_repeated_key_is_flagged_as_fan_out(mini_con):
    steps = row_count_trail(mini_con, q("pay"))
    assert steps[1].key_column == "order_id" and steps[1].key_unique is False
    assert steps[1].fan_out and steps[2].fan_out


def test_unique_key_is_not_fan_out(mini_con):
    steps = row_count_trail(mini_con, q("pay1"))
    assert [s.rows_after for s in steps] == [3, 4, 4]
    assert steps[2].key_unique is True and not steps[2].fan_out