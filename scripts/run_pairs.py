"""Run every benchmark pair and print A, B, gap and whether it matches expectation.

Run from the whydiff folder:  python scripts/run_pairs.py
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from whydiff.runner import connect, run_file  # noqa: E402


def main():
    con = connect()
    print("order_status values in the data:")
    for status, n in con.execute(
            "SELECT order_status, COUNT(*) FROM orders GROUP BY 1 ORDER BY 2 DESC").fetchall():
        print(f"  {status}: {n}")
    print()
    print(f"{'ID':<5}{'A':>18}{'B':>18}{'B - A':>18}  expected    check")
    for d in sorted((ROOT / "benchmark" / "pairs").glob("P*")):
        m = yaml.safe_load((d / "manifest.yaml").read_text())
        a = run_file(con, d / "query_a.sql")
        b = run_file(con, d / "query_b.sql")
        gap = b - a
        exp = m["expected_gap"]
        if exp == "zero":
            ok = abs(gap) < 1e-6
        elif exp == "near_zero":
            ok = abs(gap) <= 1e-4 * max(abs(a), 1.0)
        else:
            ok = abs(gap) > 1e-6
        print(f"{m['id']:<5}{a:>18,.2f}{b:>18,.2f}{gap:>18,.2f}  {exp:<10}  "
              f"{'OK' if ok else 'MISMATCH'}")
    con.close()


if __name__ == "__main__":
    main()