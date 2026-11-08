# Benchmark results

Generated 2026-11-08 18:56 from `data/olist.duckdb`. Planted causes come from each pair's manifest.yaml, not from the tool's output.

## Summary

| Metric | Value |
|---|---|
| Pairs run / completed | 16 / 16 |
| Mean cause recall (pairs with planted causes) | 100% over 15 pairs |
| Mean cause precision (pairs with reported causes) | 100% over 15 pairs |
| False positives on clean pairs | 0 over 1 pair(s) |
| Identity check passed | 16 / 16 |
| Largest identity error | 4.37e-11 |
| Single-cause pairs: max relative error | 0.000000% over 10 pairs |
| Multi-cause pairs: max order spread of one-at-a-time attribution | 8.3% over 5 pairs |
| Pairs where causes largely cancel (gross effect > 10x gap) | P15 |
| Total evaluations (distinct patched queries run) | 57 |
| Runtime per pair (mean / max, seconds) | 0.046 / 0.115 |

## Per pair

| Pair | A | B | Gap | Planted | Reported | Recall | Precision | Residual | Evals | Runtime (s) | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | 13,591,643.70 | 13,221,498.11 | -370,145.59 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.050 | ok |
| P02 | 14,209,115.34 | 13,591,643.70 | -617,471.64 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.040 | ok |
| P03 | 13,591,643.70 | 15,843,553.24 | 2,251,909.54 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.027 | ok |
| P04 | 16,008,872.12 | 15,843,553.24 | -165,318.88 | 3 | 1 | 100% | 100% | 0.00 | 2 | 0.028 | ok |
| P05 | 13,527,224.77 | 13,591,643.70 | 64,418.93 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.038 | ok |
| P06 | 14,209,115.34 | 14,209,250.31 | 134.97 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.060 | ok |
| P07 | 1,010,271.37 | 1,012,294.55 | 2,023.18 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.019 | ok |
| P08 | 99,441.00 | 96,096.00 | -3,345.00 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.047 | ok |
| P09 | 14,209,115.34 | 13,221,498.11 | -987,617.23 | 2 | 2 | 100% | 100% | 0.00 | 4 | 0.065 | ok |
| P10 | 13,591,643.70 | 15,419,773.75 | 1,828,130.05 | 2 | 2 | 100% | 100% | 0.00 | 4 | 0.046 | ok |
| P11 | 1,046,127.84 | 989,788.55 | -56,339.29 | 3 | 3 | 100% | 100% | 0.00 | 8 | 0.060 | ok |
| P12 | 112,650.00 | 98,666.00 | -13,984.00 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.035 | ok |
| P13 | 120.65 | 137.75 | 17.10 | 1 | 1 | 100% | 100% | 0.00 | 2 | 0.038 | ok |
| P14 | 13,221,498.11 | 13,221,498.11 | 0.00 | 0 | 0 | n/a | n/a | 0.00 | 1 | 0.019 | ok |
| P15 | 13,591,643.70 | 13,592,079.94 | 436.24 | 2 | 2 | 100% | 100% | 0.00 | 4 | 0.044 | ok |
| P16 | 1,046,127.84 | 1,155,443.93 | 109,316.09 | 4 | 4 | 100% | 100% | 0.00 | 16 | 0.115 | ok |

## Causes

| Pair | Cause | Kind | Effect | Share of gap |
|---|---|---|---|---|
| P01 | c1 | FILTER_DIFF | -370,145.59 | 100.0% |
| P02 | c1 | JOIN_DIFF | -617,471.64 | 100.0% |
| P03 | c1 | AGG_EXPR_DIFF | 2,251,909.54 | 100.0% |
| P04 | c1 | COMBINED | -165,318.88 | 100.0% |
| P05 | c1 | JOIN_DIFF | 64,418.93 | 100.0% |
| P06 | c1 | JOIN_TYPE_DIFF | 134.97 | 100.0% |
| P07 | c1 | TIME_DIFF | 2,023.18 | 100.0% |
| P08 | c1 | DISTINCT_DIFF | -3,345.00 | 100.0% |
| P09 | c1 | JOIN_DIFF | -604,901.12 | 61.2% |
| P09 | c2 | FILTER_DIFF | -382,716.11 | 38.8% |
| P10 | c1 | FILTER_DIFF | -396,962.54 | -21.7% |
| P10 | c2 | AGG_EXPR_DIFF | 2,225,092.59 | 121.7% |
| P11 | c1 | JOIN_DIFF | -35,240.08 | 62.5% |
| P11 | c2 | FILTER_DIFF | -22,972.49 | 40.8% |
| P11 | c3 | TIME_DIFF | 1,873.28 | -3.3% |
| P12 | c1 | DISTINCT_DIFF | -13,984.00 | 100.0% |
| P13 | c1 | AGG_EXPR_DIFF | 17.10 | 100.0% |
| P15 | c1 | AGG_EXPR_DIFF | 2,079,865.84 | 476771.0% |
| P15 | c2 | TIME_DIFF | -2,079,429.61 | -476671.0% |
| P16 | c1 | JOIN_DIFF | -38,509.17 | -35.2% |
| P16 | c2 | FILTER_DIFF | -24,650.70 | -22.5% |
| P16 | c3 | AGG_EXPR_DIFF | 170,607.08 | 156.1% |
| P16 | c4 | TIME_DIFF | 1,868.88 | 1.7% |

## Order sensitivity and cancellation (pairs with 2 or more causes)

| Pair | Order spread of one-at-a-time attribution | Gross effect / gap |
|---|---|---|
| P09 | 2.5% | 1.0 |
| P10 | 2.0% | 1.4 |
| P11 | 2.1% | 1.1 |
| P15 | 8.3% | 9,534.4 |
| P16 | 4.2% | 2.2 |

## Notes

- Order spread: largest difference for any cause between forward and reverse one-at-a-time attribution, as a percent of total absolute effect. Shapley averages over all orders, so it has no such spread.
- Gross effect / gap far above 1 means causes offset each other and percent shares are not meaningful.
- For multi-cause pairs the true split is defined by the same Shapley method, so correctness there rests on detection, the identity check and the order comparison.
