"""Stage 5b: run the held-out pairs; write results/heldout.md and results/heldout.csv.

A pair that the tool declines (unsupported construct) is recorded as 'declined',
not hidden. Nothing here changes the detectors.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_benchmark import num, run_pair, write_csv  # noqa: E402
from whydiff.attribution import AttributionError  # noqa: E402
from whydiff.benchmark import load_planted  # noqa: E402
from whydiff.evaluator import EvaluationError  # noqa: E402
from whydiff.profile import UnsupportedConstruct  # noqa: E402
from whydiff.runner import run_sql  # noqa: E402

DB = ROOT / "data" / "olist.duckdb"
HELD = ROOT / "benchmark" / "heldout"
OUT = ROOT / "results"
FIELDS = ["pair_id", "outcome", "planted", "reported", "result_a", "result_b",
          "gap", "residual", "detail"]


def classify(row, planted):
    if row["n_reported"] == 0 and not planted:
        return "correct (no cause)"
    if not planted:
        return "false positive"
    rec, prec = row["recall"], row["precision"]
    if rec == 1 and prec == 1:
        return "correct"
    bits = []
    if rec is not None and rec < 1:
        bits.append("missed cause")
    if prec is not None and prec < 1:
        bits.append("extra cause")
    return "wrong: " + " + ".join(bits or ["no match"])


def raw_values(con, d):
    try:
        return (run_sql(con, (d / "query_a.sql").read_text()),
                run_sql(con, (d / "query_b.sql").read_text()))
    except Exception:
        return None, None


def one(con, d):
    planted = load_planted(d)
    out = {"pair_id": d.name, "planted": ";".join(planted), "detail": ""}
    try:
        row, cs = run_pair(con, d)
        out.update(outcome=classify(row, planted),
                   reported="; ".join(f"{c['kind']} ({c['effect']:+,.2f})" for c in cs),
                   result_a=row["result_a"], result_b=row["result_b"],
                   gap=row["gap"], residual=row["residual"])
    except UnsupportedConstruct as e:
        out.update(outcome="declined (unsupported)", reported="", detail=str(e)[:200])
    except (EvaluationError, AttributionError) as e:
        out.update(outcome="error", reported="", detail=str(e).splitlines()[0][:200])
    except Exception as e:  # record anything unexpected instead of stopping
        out.update(outcome="error", reported="", detail=f"{type(e).__name__}: {str(e)[:150]}")
    if "result_a" not in out:
        a, b = raw_values(con, d)
        out.update(result_a=a, result_b=b, gap=None if a is None else b - a, residual=None)
    return out


def write_md(rows):
    counts: dict = {}
    for r in rows:
        key = r["outcome"].split(":")[0].split(" (")[0]
        counts[key] = counts.get(key, 0) + 1
    L = ["# Held-out results", "",
         f"Generated {datetime.now():%Y-%m-%d %H:%M} from `data/olist.duckdb`. "
         "These pairs were written by hand after the detectors were built and were not used to tune them.", "",
         "## Outcome counts", "", "| Outcome | Pairs |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(counts.items())]
    L += ["", "## Per pair", "",
          "| Pair | Outcome | Planted | Reported (effect) | A | B | Gap | Residual | Detail |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['pair_id']} | {r['outcome']} | {r['planted'] or '-'} | {r['reported'] or '-'} "
                 f"| {num(r['result_a'])} | {num(r['result_b'])} | {num(r['gap'])} "
                 f"| {num(r['residual'])} | {r['detail'] or '-'} |")
    L += ["", "## Notes", "",
          "- `declined` means the tool refused with an unsupported-construct message instead of guessing.",
          "- `wrong` and `false positive` are real failures and belong in docs/WHAT_DID_NOT_WORK.md.",
          "- If a detector is changed after seeing these results, keep this table and add a before/after note."]
    return "\n".join(L) + "\n"


def main():
    if not DB.exists():
        sys.exit(f"Database not found: {DB}")
    dirs = sorted(p for p in HELD.iterdir() if p.is_dir() and p.name.startswith("H"))
    if not dirs:
        sys.exit(f"No held-out pairs in {HELD}. Run scripts/make_heldout.py first.")
    con = duckdb.connect(str(DB), read_only=True)
    rows = []
    for d in dirs:
        r = one(con, d)
        rows.append(r)
        print(f"{d.name}: {r['outcome']}  {r['detail']}")
    OUT.mkdir(exist_ok=True)
    (OUT / "heldout.md").write_text(write_md(rows))
    write_csv(OUT / "heldout.csv", FIELDS, rows)
    print("\nWrote results/heldout.md and results/heldout.csv\n")
    print((OUT / "heldout.md").read_text())


if __name__ == "__main__":
    main()