# Held-out predictions

These predictions were written by the author (in the build chat) before the first run of
scripts/run_heldout.py. They were NOT committed to git before the run because of a command
error, so git history cannot prove the order. Treat them as honest but unverifiable.
The author had also read the detector source before predicting, so they are not blind.

| Pair | Prediction | Actual outcome (run 2026-11-09 16:17) |
|---|---|---|
| H01 | Likely correct: one FILTER_DIFF. | correct |
| H02 | Likely extra cause: unqualified vs qualified metric may be seen as a different expression (AGG_EXPR_DIFF, effect near 0) beside the real filter. | wrong: extra cause (AGG_EXPR_DIFF +0.00) |
| H03 | Likely wrong or declined: same logic written differently, but the profiles differ. | declined (unsupported) |
| H04 | Likely declined: JOIN to a CTE that aggregates is not a simple key list. | declined (unsupported) |
| H05 | Likely correct: JOIN_DIFF + FILTER_DIFF despite different aliases. Comment handling is a risk. | correct |
| H06 | Likely correct: one TIME_DIFF (boundary), since all date conditions are grouped. | correct |
