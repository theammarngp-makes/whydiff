"""Write benchmark/heldout/H01..H06 (hand-written query pairs with manifests).

Run from the whydiff folder:  python scripts/make_heldout.py
These pairs are written by hand in varied styles and are NOT used to tune the detectors.
"""
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parents[1] / "benchmark" / "heldout"

PAIRS = [
    dict(id="H01", name="no aliases vs aliases, lowercase vs uppercase keywords",
         causes=["FILTER_DIFF"], gap="nonzero",
         a="""select sum(order_items.price) as metric
from orders
join order_items on orders.order_id = order_items.order_id
""",
         b="""SELECT SUM(oi.price) AS metric
FROM orders o
INNER JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
"""),
    dict(id="H02", name="unqualified columns vs qualified columns",
         causes=["FILTER_DIFF"], gap="nonzero",
         a="""SELECT SUM(price) AS metric
FROM orders
JOIN order_items ON orders.order_id = order_items.order_id
""",
         b="""SELECT SUM(order_items.price) AS metric
FROM orders
JOIN order_items ON orders.order_id = order_items.order_id
WHERE orders.order_status = 'delivered'
"""),
    dict(id="H03", name="join+WHERE vs IN-subquery, same logic",
         causes=[], gap="zero",
         note="False-positive test: the two queries are logically equal (orders.order_id is unique).",
         a="""SELECT SUM(oi.price) AS metric
FROM order_items oi
WHERE oi.order_id IN (
    SELECT order_id FROM orders WHERE order_status = 'delivered'
)
""",
         b="""SELECT SUM(oi.price) AS metric
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
"""),
    dict(id="H04", name="CTE pre-aggregated payments vs raw payments join",
         causes=["JOIN_DIFF"], gap="nonzero",
         note="A pre-aggregates payments to one row per order; B joins raw payment rows (fan-out).",
         a="""WITH pay AS (
    SELECT order_id, SUM(payment_value) AS paid
    FROM order_payments
    GROUP BY order_id
)
SELECT SUM(oi.price) AS metric
FROM order_items oi
JOIN pay ON pay.order_id = oi.order_id
""",
         b="""SELECT SUM(oi.price) AS metric
FROM order_items oi
JOIN order_payments p ON p.order_id = oi.order_id
"""),
    dict(id="H05", name="different aliases and join order, comment, NOT IN",
         causes=["JOIN_DIFF", "FILTER_DIFF"], gap="nonzero",
         a="""-- Finance view: revenue of reviewed orders
SELECT SUM(items.price) AS metric
FROM orders AS ord
	JOIN order_reviews AS rev ON rev.order_id = ord.order_id
	JOIN order_items AS items ON ord.order_id = items.order_id
""",
         b="""SELECT SUM(i.price) AS metric
FROM orders AS o
JOIN order_items AS i
  ON o.order_id = i.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
"""),
    dict(id="H06", name="BETWEEN with date-only upper bound vs half-open range",
         causes=["TIME_DIFF"], gap="nonzero",
         note="BETWEEN ... AND '2017-11-30' stops at midnight, so 30 November orders are lost.",
         a="""SELECT SUM(oi.price) AS metric
FROM orders ord
JOIN order_items oi ON oi.order_id = ord.order_id
WHERE ord.order_purchase_timestamp BETWEEN '2017-11-01' AND '2017-11-30'
""",
         b="""SELECT SUM(oi.price) AS metric
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp >= '2017-11-01'
  AND o.order_purchase_timestamp <  '2017-12-01'
"""),
]


def main():
    for p in PAIRS:
        d = OUT / p["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "query_a.sql").write_text(p["a"])
        (d / "query_b.sql").write_text(p["b"])
        manifest = {"id": p["id"], "name": p["name"], "planted_causes": p["causes"],
                    "expected_gap": p["gap"], "note": p.get("note", "")}
        (d / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
        print("wrote", d)


if __name__ == "__main__":
    main()