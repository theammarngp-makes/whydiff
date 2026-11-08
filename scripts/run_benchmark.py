"""Stage 5: run every benchmark pair; write results/benchmark.md, .csv and _causes.csv."""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from whydiff.attribution import AttributionError, attribute  # noqa: E402
from whydiff.benchmark import load_planted, order_spread_pct, score_causes  # noqa: E402
from whydiff.evaluator import EvaluationError, Evaluator  # noqa: E402
from whydiff.profile import UnsupportedConstruct  # noqa: E402

DB = ROOT / "data" / "olist.duckdb"
PAIRS = ROOT / "benchmark" / "pairs"
OUT = ROOT / "results"
FIELDS = ["pair_id", "status", "method", "result_a", "result_b", "gap", "planted_kinds",
          "n_planted", "n_reported", "matched", "recall", "precision", "residual",
          "identity_error", "identity_ok", "evaluations", "runtime_s", "gross_effect",
          "cancellation_ratio", "order_spread_pct", "single_cause_abs_err",
          "single_cause_rel_err_pct"]
CAUSE_FIELDS = ["pair_id", "cause_id", "kind", "effect", "share_pct", "description"]


def num(x, d=2):
    return "n/a" if x is None else f"{x:,.{d}f}"


def pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


def read_sql(pdir, name):
    f = pdir / name
    if not f.exists():
        sys.exit(f"Missing {f}. Files in {pdir}: {sorted(p.name for p in pdir.iterdir())}")
    return f.read_text()


def run_pair(con, pdir):
    pid = pdir.name
    planted = load_planted(pdir)
    qa, qb = read_sql(pdir, "query_a.sql"), read_sql(pdir, "query_b.sql")
    t0 = time.perf_counter()
    ev = Evaluator(con, qa, qb)
    res = attribute(ev)
    runtime = time.perf_counter() - t0
    effects = {c["id"]: c["effect"] for c in res["causes"]}
    hit, rec, prec = score_causes(planted, ev.causes)
    gross, gap = sum(abs(x) for x in effects.values()), res["gap"]
    one = len(res["causes"]) == 1
    err = abs(res["causes"][0]["effect"] - gap) if one else None
    row = {"pair_id": pid, "status": "ok", "method": res["method"],
           "result_a": res["result_a"], "result_b": res["result_b"], "gap": gap,
           "planted_kinds": ";".join(planted), "n_planted": len(planted),
           "n_reported": len(res["causes"]), "matched": hit, "recall": rec,
           "precision": prec, "residual": res["residual"],
           "identity_error": res["identity_error"], "identity_ok": res["identity_ok"],
           "evaluations": res["evaluations"], "runtime_s": runtime, "gross_effect": gross,
           "cancellation_ratio": gross / abs(gap) if abs(gap) > 1e-9 and gross > 0 else None,
           "order_spread_pct": order_spread_pct(ev, effects),
           "single_cause_abs_err": err,
           "single_cause_rel_err_pct": (100 * err / abs(gap)) if one and abs(gap) > 1e-9 else None}
    causes = [{"pair_id": pid, "cause_id": c["id"], "kind": c["kind"], "effect": c["effect"],
               "share_pct": c["share_pct"], "description": c["description"]}
              for c in res["causes"]]
    return row, causes


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def summary_lines(rows):
    ok = [r for r in rows if r["status"] == "ok"]
    rec = [r["recall"] for r in ok if r["recall"] is not None]
    prec = [r["precision"] for r in ok if r["precision"] is not None]
    clean = [r for r in ok if r["n_planted"] == 0]
    one = [r for r in ok if r["single_cause_rel_err_pct"] is not None]
    spread = [r for r in ok if r["order_spread_pct"] is not None]
    cancel = [r for r in ok if r["cancellation_ratio"] and r["cancellation_ratio"] > 10]
    times = [r["runtime_s"] for r in ok]
    return [
        ("Pairs run / completed", f"{len(rows)} / {len(ok)}"),
        ("Mean cause recall (pairs with planted causes)", f"{pct(mean(rec))} over {len(rec)} pairs"),
        ("Mean cause precision (pairs with reported causes)", f"{pct(mean(prec))} over {len(prec)} pairs"),
        ("False positives on clean pairs", f"{sum(r['n_reported'] for r in clean)} over {len(clean)} pair(s)"),
        ("Identity check passed", f"{sum(1 for r in ok if r['identity_ok'])} / {len(ok)}"),
        ("Largest identity error", f"{max((r['identity_error'] for r in ok), default=0):.2e}"),
        ("Single-cause pairs: max relative error", f"{num(max((r['single_cause_rel_err_pct'] for r in one), default=None), 6)}% over {len(one)} pairs"),
        ("Multi-cause pairs: max order spread of one-at-a-time attribution", f"{num(max((r['order_spread_pct'] for r in spread), default=None), 1)}% over {len(spread)} pairs"),
        ("Pairs where causes largely cancel (gross effect > 10x gap)", ", ".join(r["pair_id"] for r in cancel) or "none"),
        ("Total evaluations (distinct patched queries run)", str(sum(r["evaluations"] for r in ok))),
        ("Runtime per pair (mean / max, seconds)", f"{num(mean(times), 3)} / {num(max(times, default=None), 3)}"),
    ]


def write_md(rows, causes):
    L = ["# Benchmark results", "",
         f"Generated {datetime.now():%Y-%m-%d %H:%M} from `data/olist.duckdb`. "
         "Planted causes come from each pair's manifest.yaml, not from the tool's output.", "",
         "## Summary", "", "| Metric | Value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in summary_lines(rows)]
    L += ["", "## Per pair", "",
          "| Pair | A | B | Gap | Planted | Reported | Recall | Precision | Residual | Evals | Runtime (s) | Status |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["status"] != "ok":
            L.append(f"| {r['pair_id']} | | | | | | | | | | | {r['status']} |")
            continue
        L.append(f"| {r['pair_id']} | {num(r['result_a'])} | {num(r['result_b'])} | {num(r['gap'])} "
                 f"| {r['n_planted']} | {r['n_reported']} | {pct(r['recall'])} | {pct(r['precision'])} "
                 f"| {num(r['residual'])} | {r['evaluations']} | {num(r['runtime_s'], 3)} | ok |")
    L += ["", "## Causes", "", "| Pair | Cause | Kind | Effect | Share of gap |", "|---|---|---|---|---|"]
    for c in causes:
        share = "n/a" if c["share_pct"] is None else f"{c['share_pct']:.1f}%"
        L.append(f"| {c['pair_id']} | {c['cause_id']} | {c['kind']} | {num(c['effect'])} | {share} |")
    L += ["", "## Order sensitivity and cancellation (pairs with 2 or more causes)", "",
          "| Pair | Order spread of one-at-a-time attribution | Gross effect / gap |", "|---|---|---|"]
    for r in rows:
        if r["status"] == "ok" and r["order_spread_pct"] is not None:
            L.append(f"| {r['pair_id']} | {num(r['order_spread_pct'], 1)}% | {num(r['cancellation_ratio'], 1)} |")
    L += ["", "## Notes", "",
          "- Order spread: largest difference for any cause between forward and reverse one-at-a-time "
          "attribution, as a percent of total absolute effect. Shapley averages over all orders, so it has no such spread.",
          "- Gross effect / gap far above 1 means causes offset each other and percent shares are not meaningful.",
          "- For multi-cause pairs the true split is defined by the same Shapley method, so correctness "
          "there rests on detection, the identity check and the order comparison."]
    return "\n".join(L) + "\n"


def write_csv(path, fields, data):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(data)


def main():
    if not DB.exists():
        sys.exit(f"Database not found: {DB}")
    dirs = sorted(p for p in PAIRS.iterdir() if p.is_dir() and p.name.startswith("P"))
    if not dirs:
        sys.exit(f"No pair folders in {PAIRS}")
    con = duckdb.connect(str(DB), read_only=True)
    rows, causes = [], []
    for d in dirs:
        try:
            row, cs = run_pair(con, d)
            rows.append(row)
            causes += cs
            print(f"{d.name}: ok ({row['n_reported']} causes, {row['evaluations']} evaluations)")
        except (UnsupportedConstruct, EvaluationError, AttributionError) as e:
            rows.append({"pair_id": d.name, "status": f"ERROR: {type(e).__name__}: {str(e)[:150]}"})
            print(f"{d.name}: ERROR {e}")
    OUT.mkdir(exist_ok=True)
    (OUT / "benchmark.md").write_text(write_md(rows, causes))
    write_csv(OUT / "benchmark.csv", FIELDS, rows)
    write_csv(OUT / "benchmark_causes.csv", CAUSE_FIELDS, causes)
    print("\nWrote results/benchmark.md, benchmark.csv, benchmark_causes.csv\n")
    print((OUT / "benchmark.md").read_text())
    sys.exit(0 if all(r["status"] == "ok" for r in rows) else 1)


if __name__ == "__main__":
    main()