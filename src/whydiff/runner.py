"""Run one SQL query and return its single numeric result."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "olist.duckdb"


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


def run_sql(con, sql: str) -> float:
    rows = con.execute(sql).fetchall()
    if len(rows) != 1 or len(rows[0]) != 1:
        raise ValueError("Version 1 expects exactly one row and one column.")
    value = rows[0][0]
    if value is None:
        raise ValueError("Query returned NULL.")
    return float(value)


def run_file(con, path) -> float:
    return run_sql(con, Path(path).read_text())