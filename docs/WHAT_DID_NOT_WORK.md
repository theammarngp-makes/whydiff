# What did not work

Real problems found during the build, in the order they were found. Numbers come from pasted runs.

## 1. First offsetting pair did not offset (P15)
My first cutoff counted only price. Cutting early orders also removes their freight, so the
freight added by the metric change did not cancel the lost revenue. I changed the cutoff
calculation to use price plus freight. The final P15 has a gap of 436.24 against effects of
+2,079,865.84 and -2,079,429.61.

## 2. Benchmark scorer undercounted a combined cause (P04)
When the benchmark switched to reading planted causes from manifest.yaml, P04 recall fell to
33%. The detectors had not changed: the scorer let one reported cause match only one planted
cause, but P04's three planted differences depend on each other and are reported as one
combined cause. Fix: a combined cause can match each of its members once. Lesson: a score can
be wrong even when the tool is right, so scorers need tests too.

## 3. Exports looked wrong before they were wrong
The first CSV showed floating-point noise (for example -35240.08000000229) and -0.0. A second
export was labelled "custom" because of whitespace differences. Fixes: round exported values
to 4 decimals, normalise negative zero, compare queries ignoring whitespace.

## 4. Held-out pairs: 3 correct, 2 declined, 1 wrong (run 2026-11-09 16:17)
The 16 benchmark pairs came from the templates the detectors were built around, so 100%
recall there only shows in-scope behaviour. Six hand-written pairs in other styles gave:

- **H02, wrong (extra cause).** Unqualified `price` vs `order_items.price` in a two-table
  query produced a spurious AGG_EXPR_DIFF with effect +0.00 beside the correct filter
  (-370,145.59). Confirmed by printing the profile (A: `SUM(price)`, B: `SUM(order_items.price)`): unqualified columns are only rewritten to
  a table name when the query has a single table. Not fixed in v1; a real fix needs
  schema-aware column resolution.
- **H03, declined.** Join plus filter vs `IN (subquery)`: both return 13,221,498.11, but the
  tool refused ("cannot find the condition to remove (semi-join conditions are not patchable
  in v1)"). It does not recognise that the two forms are equivalent.
- **H04, declined.** A CTE that pre-aggregates payments is not a simple key list
  ("JOIN to a CTE/subquery that is not a simple key list"). Refusing is the designed behaviour.

Declined pairs are acceptable: the tool refuses instead of guessing. H02 is the real failure,
although the extra cause is harmless in size because its effect is zero.

## 5. Process slip: predictions were not committed before the run
I intended to commit the held-out predictions before running them. A `git add` pointed at a
file that had not been created, so the commit did not happen. The predictions file now
states this. Lesson: check that a command succeeded before running the next one.