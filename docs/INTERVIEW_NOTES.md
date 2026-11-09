# Interview notes

## Stage 0: data and setup
Plain language: I loaded the nine Olist CSV files into one DuckDB file so every query runs fast and locally with no server. I printed every table's columns first so nothing in the tool depends on guessed column names.
Q: Why DuckDB? A: It is embedded (one file, no server), free, reads CSV directly and is fast for analytic aggregates.
Q: Why check the schema first? A: Assumed column names are a common source of silent errors; I built on the real output.
Q: What did you notice in the data? A: Timestamps have no timezone, customers has both customer_id and customer_unique_id, and orders can have several payment or review rows, which makes good planted bugs.

## Stage 1: runner and benchmark
Plain language: The runner executes a query and returns one number. The benchmark has 16 pairs of queries built from templates, so I know by construction which differences I planted.
Q: Why planted bugs? A: The ground truth is known, so I can measure whether the tool finds the right causes.
Q: Why a negative control (P14)? A: To check the tool does not report differences when the logic is the same.
Q: What did P15 teach you? A: My first cutoff only counted price, but cutting orders also removes their freight; the effects did not cancel until I used price plus freight. It also documents a real limitation: offsetting differences can hide a disagreement.

## Stage 2: parsing, profiles and detectors
Plain language: I turn each query into a structured profile (joins, filters, time conditions, metric) using a SQL parser instead of text matching, then compare the profiles. Anything I cannot parse or compare safely is reported as unsupported, never guessed.
Q: Why a parser (sqlglot) and not regex? A: SQL has aliases, nesting and equivalent spellings; a syntax tree gives structure, and I normalise aliases to table names so equal logic compares equal.
Q: How do you avoid false positives (P14)? A: A CTE that is only a key list is treated like IN (subquery). It is exact only if the key is unique, so later stages check it numerically and the residual would expose it.
Q: What can the detectors not see? A: Anything outside the six kinds, changed join conditions, window functions, correlated subqueries. Those become unsupported or land in the residual.
Q: Why group all date conditions into one TIME_DIFF? A: A timezone shift changes both ends of a window together; counting each bound separately would split one cause into several.
Q: How do you separate DISTINCT from aggregate differences? A: DISTINCT_DIFF when what is counted as distinct differs; AGG_EXPR_DIFF for a different expression such as price versus price plus freight.


## Stage 4: Shapley attribution
Plain language: when several differences interact, one cause's effect depends on which others are already applied. Shapley averages its effect over every possible order, so the split is fair and does not depend on the order I happened to apply them.
Q: Why Shapley instead of removing differences one at a time? A: One at a time gives different answers depending on order when causes interact. Shapley averages over all orders, is order-independent, and always sums to the total gap.
Q: How many queries does it need? A: 2^n for n causes, at most 256 for 8, which DuckDB handles easily. Above 8 I sample random orders (default 200) and label the result estimated; the total stays exact.
Q: What is the residual and when is it large? A: B minus A with every detected difference patched in. It is large when something differs that the detectors cannot see, and I report it openly instead of forcing the shares to 100%.
Q: How do you know it is right? A: Unit tests include a toy game I calculated by hand (A=20, B=30), additive and symmetric games with known answers, and an identity check on every benchmark pair. The code refuses to return a result if the identity fails.
Q: What are the limits? A: For multi-cause pairs the "true" split is defined by the same Shapley method, so I test detection and the identity there, not an independent ground truth. Attribution is relative to A and depends on the data; it is a measurement, not causal proof.

## Stage 5: Evaluation harness

**What was built (plain language):**
1. A script runs all 16 query pairs through the tool and records what it found.
2. Each pair has planted causes known by construction, so we can measure recall and precision.
3. It checks that effects plus residual equal the gap on every pair.
4. It compares Shapley with simple one-at-a-time attribution in two orders to show how order changes that simpler answer.
5. Results go to markdown and CSV, so the README and Tableau use real numbers.

**Q: How do you know the tool is right?**
A: Four checks. Detection on planted bugs (recall and precision), the identity check on every pair, the Stage 3 check that patching every difference reproduces B, and one clean pair that must produce no causes. For multi-cause pairs the true split is defined by the same Shapley method, so I say openly that these rest on detection and the identity check, not independent ground truth.

**Q: Why compare against one-at-a-time attribution?**
A: When causes interact, the effect of one depends on which others are already applied, so a one-at-a-time answer changes with the order. The benchmark measures that spread. Shapley averages all orders, so its answer does not depend on how I list the causes.

**Q: What happens when two errors cancel each other, like P15?**
A: The gap is tiny but each cause is large, with opposite signs. Because the tool compares query structure, not just the final numbers, it still lists both causes. Percent shares become meaningless there, so I report the gross effect divided by the gap and show effects in currency instead.

## Stage 7: Exports

**What was built (plain language):**
1. One click gives an Excel workbook with four sheets: Summary, Causes, RowTrail, Queries.
2. Another click gives a flat CSV, one row per cause plus a residual row, ready for Tableau.
3. Both come from the same report object the screen uses, so the screen and the files cannot disagree.
4. The workbook includes the exact queries that were run, so a finance reviewer can reproduce the result.

**Q: Why include the queries and the row trail in the Excel file?**
A: So the file stands alone. Someone who never opens the app can see the numbers, the causes, the evidence for fan-out, and the SQL that produced them.

**Q: Why a flat CSV for Tableau?**
A: Tableau works best with one row per item and a step-order column. With pair_id, step_order, effect and share_pct, a stacked bar or waterfall needs no reshaping. The residual is its own row, so unexplained amounts are visible instead of hidden.

## Stage 6 and 7 acceptance: what the evidence showed

**Q: Show me that your tool is explaining the gap and not just printing numbers.**
A: On pair P11 the report attributes a gap of -56,339.29 to three causes: an extra join to payments (62.5%), a status filter (40.8%) and a timezone shift (-3.3%), with zero residual. The row-count trail backs this up independently: query A's join to order_payments raises rows from 112,650 to 117,601 and the key repeats, which is why SUM counts orders more than once.

**Q: The trail flags order_items as fan-out in both queries. Is that a bug?**
A: No. Joining orders to order_items is an intended one-to-many join, and both queries do it, so it cancels out of the comparison. The flag is evidence that rows multiply, not proof that the join is wrong. What differs between the queries is the payments join, and that is what the tool reports as a cause.

**Q: What did you notice when checking the exports?**
A: The raw CSV had floating-point noise and negative zeros, so I rounded exported values and normalised negative zero. I also made the pair label ignore whitespace differences so a sample pair is not mislabelled as custom.

## Stage 5b: Held-out pairs

**What was built (plain language):**
1. Six query pairs written by hand in varied SQL styles (no aliases, CTEs, subqueries, comments, BETWEEN).
2. I wrote my predictions down before running, then a script sorted each result into correct, declined, wrong or false positive.
3. Result: 3 correct, 2 declined, 1 wrong.
4. The failures are written up in docs/WHAT_DID_NOT_WORK.md instead of being hidden.

**Q: Your benchmark shows 100% recall. Why should I believe it generalises?**
A: It does not, and I say so. Those 16 pairs came from the same templates the detectors were built around. On six hand-written pairs in other styles, three were correct, two were declined and one had a spurious zero-effect cause.

**Q: What was the one wrong result?**
A: With two tables in the query, an unqualified `price` and a qualified `order_items.price` were treated as different expressions, so the tool reported an extra cause with an effect of 0.00 next to the real filter. I confirmed by printing the profiles (`SUM(price)` versus `SUM(order_items.price)`) that the reason is that unqualified columns are only resolved to a table when the query has one table. A proper fix needs the table schema, so I documented it instead of patching around it.

**Q: Did you predict the outcomes first?**
A: I wrote predictions before running and they matched on all six. But I had read the code, so they were not blind, and I made a command mistake so they were not committed before the run. Git cannot prove the order, and I say that in the repo.

**Q: Is it a failure when the tool says "unsupported"?**
A: No. Declining is the designed behaviour for constructs I cannot compare safely. A wrong answer is the real failure, because a user may trust it.

## Required questions not covered earlier

**Q: What is join fan-out and how does your tool detect it?**
A: Fan-out is what happens when you join a table with several rows per order, such as payments, to order-level data. The order repeats once per payment row, so SUM counts it several times. The tool finds it two ways. First, the diff sees that a join exists in only one query (JOIN_DIFF) and measures its effect by removing it and re-running. Second, a separate diagnostic counts rows after each join. In P11, query A goes from 112,650 rows after the items join to 117,601 after the payments join. That flag is evidence, not proof, because the intended orders-to-items join is also flagged.

**Q: What would break it? What does it not support?**
A: It supports one SELECT with one aggregate and no GROUP BY. Window functions, recursive CTEs, correlated subqueries and changed join conditions are refused with a clear message. On my held-out pairs, an unqualified column in a multi-table query produced a harmless extra cause (H02), and `IN (subquery)` against join-plus-filter was refused (H03). The percent shares also become meaningless when causes offset, as in P15, so I warn and show currency effects.

**Q: How would you extend it to grouped results or other SQL dialects?**
A: For grouped results I would run the patched queries with GROUP BY, compare per group, and attribute each group's gap with the same Shapley code, plus an overall view. That needs the evaluator to return a table, not one number, and the identity check per group. For other dialects, sqlglot already parses many dialects, so the change is passing the right `read` and `write` dialect and re-running the benchmark on that engine. I tested DuckDB only, so I would not claim other dialects work until I have run them.

## Stage 8: Documentation

**What was built (plain language):**
1. A README with the demo, the real benchmark tables, the held-out results and the limits.
2. LIMITATIONS.md and a "What did not work" document, both populated from real failures.
3. A SQL Handbook module that teaches the six causes using numbers from the benchmark.
4. An MIT licence and a checklist for the first push, including a check that no Olist data or private files go public.

**Q: Why a "What did not work" section?**
A: Because every project has failures, and showing them is more credible than hiding them. A reviewer can see what I tested, what failed and what I did about it.

**Q: What would you say if asked whether this is the first tool of its kind?**
A: I would say I could not find an existing open-source tool that does this when I searched in November 2026, that the search was not exhaustive, and that Shapley attribution itself is not mine. What I did was apply it to the differences between two executed SQL queries.