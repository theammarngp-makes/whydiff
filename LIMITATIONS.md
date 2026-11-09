# Limitations

WhyDiff is a version 1 measurement tool. This page says what it does not do. Numbers refer to runs recorded in `results/`.

## What it supports

A single SELECT statement with exactly one aggregate column and no GROUP BY, run on DuckDB over the Olist tables.

## What it does not support

The tool raises "unsupported" and does not guess for:

- Window functions, recursive CTEs, correlated subqueries, `JOIN ... USING`.
- A different FROM table in the two queries, or a changed ON condition for the same join.
- A FROM that is a CTE, or a table used more than once.
- More than one aggregate column.
- GROUP BY results. Queries with different GROUP BY columns are refused, and the evaluator returns a single number, so grouped results are future work.
- A JOIN to a CTE or subquery that is not a simple key list (held-out pair H04).
- Patching semi-join differences (`IN (subquery)`) when the two sides use different forms (H03).

## Where it can be wrong or misleading

- **Attribution is relative to query A.** Shapley averages over all orders of applying the differences, but each effect is still measured as movement away from A on this data. It is a measurement, not causal proof.
- **Only the differences the detectors can see are attributed.** Anything else lands in the residual. A large residual means something differs that the six detectors cannot represent.
- **Offsetting differences can cancel.** In P15 the gap is 436.24 but the two effects are +2,079,865.84 and -2,079,429.61. The tool warns when gross effect exceeds 10 times the gap. That threshold is a heuristic. In held-out pair H05 the gross effect is about 4.9 times the gap (my arithmetic from the pasted effects), so the shares go below 0% and above 100% with no warning.
- **Dependent differences are bundled.** In P04 three planted differences are reported as one combined cause. That avoids invalid patched queries but loses detail.
- **Unqualified columns in multi-table queries (H02).** `price` and `order_items.price` were treated as different expressions, producing an extra cause with effect +0.00. Confirmed by printing the profile (A: `SUM(price)`, B: `SUM(order_items.price)`): the reason is that the profile only resolves an unqualified column to a table when the query has a single table. A proper fix needs schema-aware resolution.
- **Time columns are found by a name heuristic** (names containing `timestamp`, `date`, or ending in `_at`). A date column with another name would be treated as an ordinary filter.
- **All date conditions are grouped into one `TIME_DIFF`.** This avoids splitting one timezone shift into several causes, but separate date problems in one pair cannot be separated.
- **The row-count trail ignores WHERE filters and semi-joins.** The fan-out flag is evidence that rows multiply, not proof that a join is wrong. The intended `orders` to `order_items` join is also flagged.
- **Exact Shapley needs 2^n runs.** Above 8 causes the tool samples permutations (default 200) and labels the result "estimated". The total stays exact.

## About the evidence

- The 16 benchmark pairs were built from templates that the detectors were designed around. The 100% recall in `results/benchmark.md` shows in-scope behaviour, not generalisation.
- For multi-cause pairs the "true" split is defined by the same Shapley method, so those results are checked by detection, the identity check and a comparison with one-at-a-time attribution, not by independent ground truth.
- The held-out set has six pairs: 3 correct, 2 declined, 1 wrong. That is a small sample.
- The held-out predictions were written before the run but not committed before it, and the author had read the detector code first.
- One dataset (Olist), one dialect (DuckDB), synthetic planted bugs. Real company queries may differ.
- Tested on macOS with Python 3.14 only.

## Data

The Olist data is not part of this repository. Download it from Kaggle and check its licence there.