# PROGRESS
Last updated: 2026-11-08 | Session number: 2

## Current stage
Stage 5b (held-out pairs) then Stage 8 (docs) | Status: not started. Stages 0-7 done and committed.

## Completed
- [x] Stage 0: setup, data load, schema
- [x] Stage 1: runner and 16 benchmark pairs
- [x] Stage 2: profiles and six detectors
- [x] Stage 3: patchers and evaluator (A + all patches = B for all 16 pairs, shortfall 0.0000)
- [x] Stage 4: attribution engine (identity ok 16/16, max error 4.37e-11)
- [x] Stage 5: evaluation harness (benchmark reads planted causes from manifest.yaml; P04 scorer fixed)
- [x] Stage 6: Streamlit app, accepted on P11 (summary, causes table, waterfall, two row-count trails)
- [x] Stage 7: exporters, accepted: Excel (Summary, Causes, RowTrail, Queries) and Tableau CSV verified against benchmark numbers

## Pending small checks
- [x] Session-2 edits applied; pytest 80 passed
- [x] CSV opened in Tableau Public: bar chart of effects by cause, SUM(Effect) = -56,339 = P11 gap
- [x] .gitignore covers data/, .venv/, *.duckdb, caches; private brief PDF untracked
- [x] Local git repo; first commit b927757 "Stages 0-7 complete"; no remote, not pushed
- [x] App checks passed: P11 (3 causes, residual 0), P14 (CTE vs IN-subquery: same value, no differences), P15 (cancel-out warning, effects +2,079,865.84 / -2,079,429.61, gross 4,159,295.45)
- [x] Screenshots saved in docs/screenshots/: p11_result.png (retaken, correct), p14_no_difference.png, p15_offsetting.png, tableau_p11_effects.png
- [x] app.py: sample-pair dropdown auto-loads (on_change=load_sample)

## Files delivered so far
| Path | Status | Notes |
|---|---|---|
| requirements.txt, requirements-lock.txt | final | pinned |
| .gitignore, pytest.ini, tests/conftest.py | final | verify .gitignore excludes data/, .venv/, olist.duckdb |
| src/whydiff/loader.py, runner.py, profile.py, detectors.py, patchers.py, evaluator.py, attribution.py | final | |
| src/whydiff/benchmark.py | final | load_planted, score_causes (combined cause matches each member once), order_spread_pct, PLANTED |
| src/whydiff/diagnostics.py, report.py | final | |
| src/whydiff/exporters.py | final + edit pending | add _r rounding helper |
| app.py | final + edit pending | pair_label whitespace edit |
| scripts/make_pairs.py, run_pairs.py, run_detect.py, run_evaluate.py, run_attribution.py, run_benchmark.py | final | |
| tests/ (detectors, evaluator, attribution, benchmark, manifests, diagnostics, report, exporters) | final | exporters tests need a run; one new test pending |
| results/benchmark.md, benchmark.csv, benchmark_causes.csv | generated | real run 2026-11-08 18:56 |
| INTERVIEW_NOTES.md | in progress | Ammar must have pasted sections for Stages 0-7 |
Not yet created: README.md, LIMITATIONS.md, LICENSE, docs/module_why_queries_disagree.md, screenshots, held-out pairs.

## Environment (real)
Mac, Python 3.14, venv ~/whydiff/.venv, DuckDB file data/olist.duckdb, CSVs in data/raw/. App runs at localhost:8501 (`streamlit run app.py`).
Pinned: duckdb 2.0.0, sqlglot 30.30.0, pandas 3.1.1, streamlit 1.67.0, plotly 7.1.0, openpyxl 3.1.5, pytest 9.2.0, PyYAML 6.0.3.

## Real results pasted by Ammar
Row counts: customers 99441; geolocation 1000163; order_items 112650; order_payments 103886; order_reviews 99224; orders 99441; product_category_name_translation 71; products 32951; sellers 3095.
Key columns: orders(order_id, customer_id, order_status, order_purchase_timestamp, ...); order_items(order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value); order_payments(order_id, payment_sequential, payment_type, payment_installments, payment_value); order_reviews(review_id, order_id, review_score, ...); customers(customer_id, customer_unique_id, ...).
order_status counts: delivered 96478, shipped 1107, canceled 625, unavailable 609, invoiced 314, processing 301, created 5, approved 2.
Manifest format: id, name, planted_causes (list of kinds), expected_gap, note. Pair folder: manifest.yaml, query_a.sql, query_b.sql. Metric alias in pair queries: metric. P04 manifest: JOIN_DIFF, JOIN_DIFF, AGG_EXPR_DIFF (source-table swap), reported as one COMBINED cause with exactly those three members.
Benchmark A / B (causes after bundling): P01 13,591,643.70 / 13,221,498.11 (1); P02 14,209,115.34 / 13,591,643.70 (1); P03 13,591,643.70 / 15,843,553.24 (1); P04 16,008,872.12 / 15,843,553.24 (1, COMBINED of 3); P05 13,527,224.77 / 13,591,643.70 (1); P06 14,209,115.34 / 14,209,250.31 (1); P07 1,010,271.37 / 1,012,294.55 (1); P08 99,441 / 96,096 (1); P09 14,209,115.34 / 13,221,498.11 (2); P10 13,591,643.70 / 15,419,773.75 (2); P11 1,046,127.84 / 989,788.55 (3); P12 112,650 / 98,666 (1); P13 120.65 / 137.75 (1); P14 13,221,498.11 / 13,221,498.11 (0); P15 13,591,643.70 / 13,592,079.94 (2); P16 1,046,127.84 / 1,155,443.93 (4).
Attribution (exact Shapley, residual 0.00 on all 16): single-cause pairs 100% on their one cause; P09 JOIN -604,901.12 (61.2%), FILTER -382,716.11 (38.8%); P10 FILTER -396,962.54 (-21.7%), AGG_EXPR 2,225,092.59 (121.7%); P11 JOIN -35,240.08 (62.5%), FILTER -22,972.49 (40.8%), TIME 1,873.28 (-3.3%); P15 AGG_EXPR 2,079,865.84, TIME -2,079,429.61 (shares +/-476,771%, gap 436.24); P16 JOIN -38,509.17 (-35.2%), FILTER -24,650.70 (-22.5%), AGG_EXPR 170,607.08 (156.1%), TIME 1,868.88 (1.7%).
Benchmark summary (real run 2026-11-08 18:56, manifests as ground truth): 16/16 pairs completed; mean recall 100% over 15 pairs; mean precision 100% over 15 pairs; identity check 16/16 (largest error 4.37e-11); single-cause max relative error 0.000000% over 10 pairs; max order spread of one-at-a-time attribution 8.3% (P09 2.5%, P10 2.0%, P11 2.1%, P15 8.3%, P16 4.2%); gross effect / gap: P09 1.0, P10 1.4, P11 1.1, P15 9,534.4, P16 2.2; total evaluations 57; runtime per pair mean 0.047s, max about 0.116s. pytest: 76 passed (before exporters tests).
App and exports (real, P11): app shows summary "Gap = -56,339.29: 63% join, 41% filter, -3% time (no unexplained residual)", Exact Shapley, 8 patched queries, identity error 0. Excel has sheets Summary, Causes, RowTrail, Queries. Row trail P11: query A orders 99,441 -> order_items 112,650 (fan_out True, intended grain, in both queries) -> order_payments 117,601 (fan_out True, the real cause); query B orders -> order_items 112,650. CSV columns: pair_id, step_order, cause, kind, effect, share_pct, description (residual its own row). Second export was labelled "custom" (whitespace/edit; pair_label fix pending). CSV showed float noise (-35240.08000000229) and -0.0 (rounding fix pending).
Event during Stage 5: when the benchmark switched to manifests, P04 recall fell to 33% because the old scorer let one reported cause match only one planted cause; fixed by letting a combined cause match each member once. Use as a "what did not work" item.
pytest: 80 passed after exporters tests and the rounding test.
## Code interfaces
- profile.build_profile(sql) -> QueryProfile; raises UnsupportedConstruct.
- detectors.diff_profiles(pa, pb) -> list[Difference(id, kind, description, payload)].
- patchers.apply_patches(pa, pb, diffs) -> SQL text of A patched.
- evaluator.Evaluator(con, sql_a, sql_b): .causes (Cause(id, kind, description, members)), .result_a, .result_b, .v(subset), .all_ids, .n_evaluations, .sql_log, .shortfall().
- attribution.attribute(ev, max_exact=8, n_perm=200, seed=0) -> dict(result_a, result_b, gap, method, causes[{id, kind, description, members, effect, share_pct}], residual, residual_share_pct, identity_error, identity_ok, evaluations, runtime_s). Also shapley_exact, shapley_monte_carlo, sequential_attribution.
- benchmark: PLANTED, load_planted(pair_dir), score_causes(planted, causes) -> (matched, recall, precision), order_spread_pct(ev, effects).
- diagnostics.row_count_trail(con, sql) -> list[JoinStep]; counts raw join output (no WHERE, no semi-joins).
- report: is_offsetting, summarize, waterfall_steps, build_report(con, sql_a, sql_b, max_exact=8) -> dict(summary, offsetting, attribution, waterfall, trail_a, trail_b).
- exporters: cause_rows(report, pair_id), causes_csv_bytes(report, pair_id), excel_bytes(report, sql_a, sql_b, pair_id).

## Decisions log
- Table names strip "olist_" prefix and "_dataset" suffix; pairs built from templates; P15 cutoff uses price + freight.
- Detectors return Difference objects with payloads; patch functions live in patchers.py.
- TIME_DIFF groups all date conditions; time columns found by name heuristic.
- DISTINCT_DIFF = what is counted distinct differs; AGG_EXPR_DIFF = other metric change (incl. P13).
- Semi-join differences are not patchable in v1.
- Dependent differences are bundled into one COMBINED cause (P04). Trade-off: less detail. Future option: precedence-constrained Shapley.
- Scoring: a COMBINED cause can match each of its member differences once; precision = reported causes matching at least one planted kind. Ground truth from manifest.yaml; PLANTED is a design table checked by tests/test_manifests.py.
- Offsetting pairs (gross > 10x gap): report currency effects and warn that shares are not meaningful.
- Waterfall axis zoomed to the gap.
- Exports built from the same report dict as the screen; residual always its own row; exported values rounded to 4 decimals.
- Do not publish the Olist data: .gitignore must exclude data/, .venv/, olist.duckdb.

## Known issues / bugs
- Benchmark pairs come from the same templates the detectors were built around, so 100% recall shows in-scope behaviour, not generalisation. Plan: held-out hand-written pairs (Stage 5b); report failures honestly.
- Multi-cause ground truth is defined by the same Shapley method (state in README).
- Row-count trail ignores WHERE filters and semi-joins; the fan-out flag is evidence, not proof (the intended orders -> order_items join is also flagged).
- Group-by, join-ON differences and different FROM tables raise unsupported.

## Remaining work
- [ ] Pending small checks above
- [ ] Stage 5b: 5-6 held-out hand-written pairs in varied SQL styles (different aliases, no aliases, CTEs, subqueries, uppercase/lowercase, different formatting); run through the tool; record real successes and failures in docs/WHAT_DID_NOT_WORK.md; add the ones that run to benchmark/heldout/ with manifests and a separate results table
- [ ] Stage 8: README.md (brief Section 17 wording, exact sentence "I could not find an existing open-source tool that does this (searched November 2026)", real benchmark table, screenshot of P11 and P15), LIMITATIONS.md, INTERVIEW_NOTES.md cleanup, docs/module_why_queries_disagree.md (SQL Handbook module draft), MIT LICENSE, GitHub description and topics, first push

## Exact first action next session
Paste the brief, this PROGRESS.md, the attached source files listed in the handoff, and: output of `python -m pytest -q`; app results for P14 and P15; whether the CSV opened in Tableau Public; `cat .gitignore`. Then confirm the small checks, start Stage 5b (write 5-6 held-out pairs, give me the run command, paste results), then do Stage 8.