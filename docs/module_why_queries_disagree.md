# Module: Why two queries for the same metric disagree

**Level:** intermediate. **Dataset:** Olist Brazilian e-commerce (`orders`, `order_items`, `order_payments`, `order_reviews`, `customers`).

Two analysts write "total revenue" and get different numbers. This module teaches the six SQL differences that cause most disagreements, how to confirm each one, and a repeatable way to diagnose them. The numbers are real results from the WhyDiff benchmark.

## Learning goals

- Define grain and explain join fan-out.
- Recognise six causes of metric disagreement.
- Prove a cause by changing one thing at a time and re-running.
- Explain why several causes need a fair way to split the gap.

## 1. Grain and fan-out

**Grain** is what one row of a table means: one order, one order item, one payment. `orders` has one row per order. `order_items` has one row per item, and `order_payments` can have several rows per order.

**Fan-out** happens when you join a one-to-many table to something at order level. Each parent row is repeated once per child row, so `SUM` counts it several times.

Check it by counting rows before and after a join:

```sql
SELECT COUNT(*) FROM orders o JOIN order_items oi ON oi.order_id = o.order_id;        -- 112,650
SELECT COUNT(*) FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
                             JOIN order_payments p ON p.order_id = o.order_id;         -- 117,601
```

(These two counts are the row-count trail for P11, query A, before its date filter.) Rows grew from 112,650 to 117,601 although no new orders were added.

## 2. The six causes

| # | Cause | Query A | Query B | Result A | Result B |
|---|---|---|---|---|---|
| 1 | Filter | no status filter | `o.order_status = 'delivered'` | 13,591,643.70 | 13,221,498.11 |
| 2 | Join fan-out | also joins `order_payments` | no payments join | 14,209,115.34 | 13,591,643.70 |
| 3 | Aggregate expression | `SUM(oi.price)` | `SUM(oi.price + oi.freight_value)` | 13,591,643.70 | 15,843,553.24 |
| 4 | Join type | `JOIN order_payments` | `LEFT JOIN order_payments` | 14,209,115.34 | 14,209,250.31 |
| 5 | Time boundary | November 2017 on the raw timestamp | same window with the timestamp shifted by 3 hours | 1,010,271.37 | 1,012,294.55 |
| 6 | Distinctness | `COUNT(DISTINCT c.customer_id)` | `COUNT(DISTINCT c.customer_unique_id)` | 99,441 | 96,096 |

Two more grain examples from the benchmark:

- `COUNT(*)` versus `COUNT(DISTINCT o.order_id)` after joining items: 112,650 versus 98,666 (rows versus orders).
- `AVG(oi.price)` versus `SUM(oi.price) / COUNT(DISTINCT o.order_id)`: 120.65 versus 137.75 (average per item versus average per order).

### Notes on each cause

1. **Filter.** One query includes cancelled or unavailable orders and the other does not.
2. **Fan-out.** The payments join repeats an order once per payment row.
3. **Aggregate expression.** Revenue with or without freight is a business definition, not a bug, so agree on it in writing.
4. **Join type.** `INNER JOIN` drops orders with no matching row and `LEFT JOIN` keeps them. The gap is small (+134.97) because almost every order has a payment row.
5. **Time boundary.** Timestamps carry no timezone. A fixed offset moves orders across the month boundary.
6. **Distinctness.** `customer_id` identifies a customer record per order, and `customer_unique_id` identifies a person.

## 3. A diagnosis routine

1. Run both queries and write down both numbers.
2. List every difference between the two SQL texts: tables, join types, WHERE conditions, the aggregate, date handling.
3. For each difference, change query A so it matches query B on that one point only, re-run, and record how far the number moves.
4. Change all of them at once. If you reach B's number, you found everything. If not, the leftover is the **residual**, meaning something you did not list.
5. Count rows after each join to check for fan-out.

## 4. When causes interact

Step 3 above gives different answers depending on the order you apply the changes, because the effect of a change depends on what is already applied. Example, P11 (payments join, status filter, timezone shift). The **Shapley** method averages each change's effect over every order. With three causes that is 2^3 = 8 query runs. For P11 it gives:

| Cause | Effect on A | Share of gap |
|---|---|---|
| Payments join | -35,240.08 | 62.5% |
| Status filter | -22,972.49 | 40.8% |
| Timezone shift | +1,873.28 | -3.3% |

Gap = 989,788.55 - 1,046,127.84 = -56,339.29, residual 0.00. A negative share means that cause pushed the number the other way.

## 5. Offsetting errors

Two causes can cancel. In pair P15 the effects are +2,079,865.84 (freight added) and -2,079,429.61 (early orders cut), but the gap is only 436.24. Matching totals do not prove matching logic.

## Exercises

1. Write a query for revenue by status that does not suffer fan-out from payments. (Hint: aggregate payments to one row per order in a CTE first.)
2. Write two queries for "customers" that return 99,441 and 96,096. Explain the difference in one sentence.
3. Take the two queries in cause 5 and shift the window by 5 hours instead of 3. Predict whether the result goes up or down, then run it.
4. Explain why a `LEFT JOIN` to `order_payments` changes `SUM(oi.price)` by only +134.97.

## Tool

The WhyDiff repository automates steps 2 to 5 for two queries: see the README.