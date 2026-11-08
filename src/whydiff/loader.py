"""Load Olist CSVs into DuckDB and print the real schema.

Usage (from the whydiff folder, venv active):
    python src/whydiff/loader.py load
    python src/whydiff/loader.py schema
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "olist.duckdb"


def table_name(stem: str) -> str:
    """olist_orders_dataset -> orders (other names are kept as they are)."""
    name = stem
    if name.startswith("olist_"):
        name = name[len("olist_"):]
    if name.endswith("_dataset"):
        name = name[: -len("_dataset")]
    return name


def load() -> None:
    files = sorted(CSV_DIR.glob("*.csv"))
    if not files:
        sys.exit(f"No CSV files found in {CSV_DIR}")
    con = duckdb.connect(str(DB_PATH))
    for f in files:
        name = table_name(f.stem)
        con.execute(
            f"CREATE OR REPLACE TABLE {name} AS "
            f"SELECT * FROM read_csv_auto('{f}', header=true)"
        )
        print(f"loaded {f.name} -> table {name}")
    con.close()
    print(f"\nDatabase written to {DB_PATH}")


def schema() -> None:
    if not DB_PATH.exists():
        sys.exit("Database not found. Run the 'load' command first.")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name").fetchall()]
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"\n=== {t}  ({n} rows) ===")
        for col, dtype, *_ in con.execute(f"DESCRIBE {t}").fetchall():
            print(f"  {col}  {dtype}")
    con.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "load":
        load()
    elif cmd == "schema":
        schema()
    else:
        sys.exit("Usage: python src/whydiff/loader.py [load|schema]")