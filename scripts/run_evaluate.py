"""For every benchmark pair: patch ALL detected differences into A and compare with B.

Run from the whydiff folder:  python scripts/run_evaluate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from whydiff.evaluator import Evaluator  # noqa: E402
from whydiff.runner import connect  # noqa: E402


def main():
    con = connect()
    print(f"{'ID':<5}{'causes':>7}{'A':>16}{'B':>16}{'A + all patches':>18}{'B - patched':>14}  check")
    for d in sorted((ROOT / "benchmark" / "pairs").glob("P*")):
        ev = Evaluator(con, (d / "query_a.sql").read_text(), (d / "query_b.sql").read_text())
        full = ev.v(ev.all_ids)
        short = ev.shortfall()
        ok = abs(short) <= 1e-6 * max(1.0, abs(ev.result_b))
        print(f"{d.name:<5}{len(ev.causes):>7}{ev.result_a:>16,.2f}{ev.result_b:>16,.2f}"
              f"{full:>18,.2f}{short:>14,.4f}  {'OK' if ok else 'SHORTFALL'}")
    con.close()


if __name__ == "__main__":
    main()