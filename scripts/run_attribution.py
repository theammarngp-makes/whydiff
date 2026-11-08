"""Attribute the gap of every benchmark pair to its causes (real data).

Run from the whydiff folder:  python scripts/run_attribution.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from whydiff.attribution import attribute  # noqa: E402
from whydiff.evaluator import Evaluator  # noqa: E402
from whydiff.runner import connect  # noqa: E402


def pct(x):
    return "n/a" if x is None else f"{x:,.1f}%"


def main():
    con = connect()
    for d in sorted((ROOT / "benchmark" / "pairs").glob("P*")):
        ev = Evaluator(con, (d / "query_a.sql").read_text(), (d / "query_b.sql").read_text())
        r = attribute(ev)
        print(f"\n{d.name}  A={r['result_a']:,.2f}  B={r['result_b']:,.2f}  gap={r['gap']:,.2f}  "
              f"[{r['method']}, {r['evaluations']} evaluations, {r['runtime_s']:.2f}s]")
        for c in r["causes"]:
            print(f"    {c['id']} {c['kind']:<15}{c['effect']:>16,.2f}  {pct(c['share_pct']):>10}  "
                  f"{c['description'][:70]}")
        print(f"    residual{'':<13}{r['residual']:>16,.2f}  {pct(r['residual_share_pct']):>10}"
              f"   identity error {r['identity_error']:.2e}")
    con.close()


if __name__ == "__main__":
    main()