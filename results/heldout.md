# Held-out results

Generated 2026-11-09 16:17 from `data/olist.duckdb`. These pairs were written by hand after the detectors were built and were not used to tune them.

## Outcome counts

| Outcome | Pairs |
|---|---|
| correct | 3 |
| declined | 2 |
| wrong | 1 |

## Per pair

| Pair | Outcome | Planted | Reported (effect) | A | B | Gap | Residual | Detail |
|---|---|---|---|---|---|---|---|---|
| H01 | correct | FILTER_DIFF | FILTER_DIFF (-370,145.59) | 13,591,643.70 | 13,221,498.11 | -370,145.59 | 0.00 | - |
| H02 | wrong: extra cause | FILTER_DIFF | FILTER_DIFF (-370,145.59); AGG_EXPR_DIFF (+0.00) | 13,591,643.70 | 13,221,498.11 | -370,145.59 | 0.00 | - |
| H03 | declined (unsupported) | - | - | 13,221,498.11 | 13,221,498.11 | 0.00 | n/a | cannot find the condition to remove (semi-join conditions are not patchable in v1) |
| H04 | declined (unsupported) | JOIN_DIFF | - | 13,591,508.73 | 14,209,115.34 | 617,606.61 | n/a | JOIN to a CTE/subquery that is not a simple key list |
| H05 | correct | JOIN_DIFF;FILTER_DIFF | JOIN_DIFF (+63,467.44); FILTER_DIFF (-96,291.47) | 13,527,224.77 | 13,494,400.74 | -32,824.03 | 0.00 | - |
| H06 | correct | TIME_DIFF | TIME_DIFF (+31,322.74) | 978,948.63 | 1,010,271.37 | 31,322.74 | 0.00 | - |

## Notes

- `declined` means the tool refused with an unsupported-construct message instead of guessing.
- `wrong` and `false positive` are real failures and belong in docs/WHAT_DID_NOT_WORK.md.
- If a detector is changed after seeing these results, keep this table and add a before/after note.
