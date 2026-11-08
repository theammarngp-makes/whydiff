"""Generate benchmark/pairs/P01..P16 (query_a.sql, query_b.sql, manifest.yaml).

Run from the whydiff folder:  python scripts/make_pairs.py
Pair P15 needs the database (it picks a date cutoff from the data).
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from whydiff.runner import connect  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "benchmark" / "pairs"

ITEMS = "FROM orders o\nJOIN order_items oi ON oi.order_id = o.order_id"
PAY_INNER = "\nJOIN order_payments p ON p.order_id = o.order_id"
PAY_LEFT = "\nLEFT JOIN order_payments p ON p.order_id = o.order_id"
REVIEWS = "\nJOIN order_reviews r ON r.order_id = o.order_id"
CUST = "FROM orders o\nJOIN customers c ON c.customer_id = o.customer_id"
DELIVERED = "o.order_status = 'delivered'"
TS = "o.order_purchase_timestamp"
WIN = [f"{TS} >= TIMESTAMP '2017-11-01 00:00:00'",
       f"{TS} < TIMESTAMP '2017-12-01 00:00:00'"]
WIN_SHIFT = [f"{TS} - INTERVAL 3 HOUR >= TIMESTAMP '2017-11-01 00:00:00'",
             f"{TS} - INTERVAL 3 HOUR < TIMESTAMP '2017-12-01 00:00:00'"]
PRICE = "SUM(oi.price)"
PRICE_FRT = "SUM(oi.price + oi.freight_value)"


def sql(select, frm, where=()):
    s = f"SELECT {select} AS metric\n{frm}"
    if where:
        s += "\nWHERE " + "\n  AND ".join(where)
    return s + ";\n"


def pick_p15_cutoff(con) -> str:
    """Cutoff t so that revenue dropped by 'ts < t' roughly equals total freight added."""
    freight = con.execute(
        "SELECT SUM(oi.freight_value) FROM orders o "
        "JOIN order_items oi ON oi.order_id = o.order_id").fetchone()[0]
    ts = con.execute(f"""
        WITH t AS (SELECT o.order_purchase_timestamp AS ts, SUM(oi.price + oi.freight_value) AS p
                   FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
                   GROUP BY 1),
        c AS (SELECT ts, SUM(p) OVER (ORDER BY ts DESC) AS tail FROM t)
        SELECT ts FROM c ORDER BY ABS(tail - {freight}) LIMIT 1""").fetchone()[0]
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def pair(pid, name, a, b, causes, gap, note=""):
    return dict(id=pid, name=name, a=a, b=b, causes=causes, gap=gap, note=note)


def build_pairs(con):
    cut = pick_p15_cutoff(con)
    cutoff_pred = f"{TS} < TIMESTAMP '{cut}'"
    return [
        pair("P01", "status filter",
             sql(PRICE, ITEMS), sql(PRICE, ITEMS, [DELIVERED]),
             ["FILTER_DIFF"], "nonzero"),
        pair("P02", "payments fan-out",
             sql(PRICE, ITEMS + PAY_INNER), sql(PRICE, ITEMS),
             ["JOIN_DIFF"], "nonzero"),
        pair("P03", "price vs price+freight",
             sql(PRICE, ITEMS), sql(PRICE_FRT, ITEMS),
             ["AGG_EXPR_DIFF"], "nonzero"),
        pair("P04", "payment_value vs price+freight",
             sql("SUM(p.payment_value)",
                 "FROM orders o\nJOIN order_payments p ON p.order_id = o.order_id"),
             sql(PRICE_FRT, ITEMS),
             ["JOIN_DIFF", "JOIN_DIFF", "AGG_EXPR_DIFF"], "nonzero",
             "Different source tables: A joins payments, B joins items, and the aggregate differs. Residual to be measured in Stage 3."),
        pair("P05", "reviews fan-out",
             sql(PRICE, ITEMS + REVIEWS), sql(PRICE, ITEMS),
             ["JOIN_DIFF"], "nonzero"),
        pair("P06", "INNER vs LEFT join to payments",
             sql(PRICE, ITEMS + PAY_INNER), sql(PRICE, ITEMS + PAY_LEFT),
             ["JOIN_TYPE_DIFF"], "nonzero",
             "Gap may be small if almost every order has a payment row."),
        pair("P07", "timezone shift of 3 hours, November 2017",
             sql(PRICE, ITEMS, WIN), sql(PRICE, ITEMS, WIN_SHIFT),
             ["TIME_DIFF"], "nonzero"),
        pair("P08", "customer_id vs customer_unique_id",
             sql("COUNT(DISTINCT c.customer_id)", CUST),
             sql("COUNT(DISTINCT c.customer_unique_id)", CUST),
             ["DISTINCT_DIFF"], "nonzero"),
        pair("P09", "status filter + payments fan-out",
             sql(PRICE, ITEMS + PAY_INNER), sql(PRICE, ITEMS, [DELIVERED]),
             ["FILTER_DIFF", "JOIN_DIFF"], "nonzero"),
        pair("P10", "status filter + freight included",
             sql(PRICE, ITEMS), sql(PRICE_FRT, ITEMS, [DELIVERED]),
             ["FILTER_DIFF", "AGG_EXPR_DIFF"], "nonzero"),
        pair("P11", "payments fan-out + status filter + timezone",
             sql(PRICE, ITEMS + PAY_INNER, WIN),
             sql(PRICE, ITEMS, [DELIVERED] + WIN_SHIFT),
             ["JOIN_DIFF", "FILTER_DIFF", "TIME_DIFF"], "nonzero"),
        pair("P12", "COUNT(*) vs COUNT(DISTINCT order_id)",
             sql("COUNT(*)", ITEMS), sql("COUNT(DISTINCT o.order_id)", ITEMS),
             ["DISTINCT_DIFF"], "nonzero"),
        pair("P13", "AVG(price) vs SUM(price)/COUNT(DISTINCT order_id)",
             sql("AVG(oi.price)", ITEMS),
             sql("SUM(oi.price) / COUNT(DISTINCT o.order_id)", ITEMS),
             ["AGG_EXPR_DIFF"], "nonzero"),
        pair("P14", "CTE vs subquery, same logic",
             "WITH d AS (\n  SELECT order_id FROM orders WHERE order_status = 'delivered'\n)\n"
             "SELECT SUM(oi.price) AS metric\nFROM order_items oi\n"
             "JOIN d ON d.order_id = oi.order_id;\n",
             "SELECT SUM(oi.price) AS metric\nFROM order_items oi\n"
             "WHERE oi.order_id IN (\n  SELECT order_id FROM orders WHERE order_status = 'delivered'\n);\n",
             [], "zero", "False-positive test: no cause should be reported."),
        pair("P15", "offsetting errors (freight added, early orders cut)",
             sql(PRICE, ITEMS), sql(PRICE_FRT, ITEMS, [cutoff_pred]),
             ["AGG_EXPR_DIFF", "TIME_DIFF"], "near_zero",
             f"Cutoff {cut} chosen from the data so the two effects roughly cancel."),
        pair("P16", "four causes combined",
             sql(PRICE, ITEMS + PAY_INNER, WIN),
             sql(PRICE_FRT, ITEMS, [DELIVERED] + WIN_SHIFT),
             ["JOIN_DIFF", "FILTER_DIFF", "AGG_EXPR_DIFF", "TIME_DIFF"], "nonzero"),
    ]


def main():
    con = connect()
    for p in build_pairs(con):
        d = OUT / p["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "query_a.sql").write_text(p["a"])
        (d / "query_b.sql").write_text(p["b"])
        manifest = {"id": p["id"], "name": p["name"],
                    "planted_causes": p["causes"],
                    "expected_gap": p["gap"], "note": p["note"]}
        (d / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
        print("wrote", d)
    con.close()


if __name__ == "__main__":
    main()