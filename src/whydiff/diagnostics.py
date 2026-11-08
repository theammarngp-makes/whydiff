"""Row-count trail: rows after each join step, and whether the joined key repeats."""
from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from .profile import build_profile


@dataclass
class JoinStep:
    step: int
    table: str
    join_kind: str            # BASE for the starting table
    rows_before: int
    rows_after: int
    key_column: str | None    # column of the joined table in a simple ON equality
    key_unique: bool | None   # None when the key could not be identified
    multiplies: bool          # row count rose at this step
    fan_out: bool             # row count rose AND the joined key repeats
    note: str


def _key_column(on: str, table: str):
    if not on:
        return None
    try:
        node = sqlglot.parse_one(on, read="duckdb")
    except SqlglotError:
        return None
    if not isinstance(node, exp.EQ):
        return None
    cols = [s for s in (node.this, node.expression) if isinstance(s, exp.Column)]
    mine = [c.name for c in cols if c.table == table]
    return mine[0] if len(cols) == 2 and len(mine) == 1 else None


def _one(con, sql):
    return con.execute(sql).fetchone()


def row_count_trail(con, sql: str) -> list:
    """Rows after each plain-table join. WHERE filters and semi-joins are not applied."""
    prof = build_profile(sql)
    from_sql = prof.base_table
    prev = _one(con, f"SELECT COUNT(*) FROM {from_sql}")[0]
    steps = [JoinStep(0, prof.base_table, "BASE", prev, prev, None, None, False, False,
                      "Starting rows")]
    for i, j in enumerate(prof.joins, start=1):
        from_sql += f" {j.kind} JOIN {j.table}" + (f" ON {j.on}" if j.on else "")
        rows = _one(con, f"SELECT COUNT(*) FROM {from_sql}")[0]
        key = _key_column(j.on, j.table)
        unique = None
        if key:
            n, d = _one(con, f"SELECT COUNT({key}), COUNT(DISTINCT {key}) FROM {j.table}")
            unique = n == d
        multiplies = rows > prev
        fan = multiplies and unique is False
        if fan:
            note = (f"Rows rose from {prev:,} to {rows:,} and {j.table}.{key} repeats, so each "
                    "earlier row can appear several times. Amounts at the earlier grain get counted repeatedly.")
        elif multiplies:
            note = f"Rows rose from {prev:,} to {rows:,}; key uniqueness could not be confirmed."
        elif rows < prev:
            note = f"Rows fell from {prev:,} to {rows:,}: unmatched rows were dropped."
        else:
            note = "Row count unchanged."
        steps.append(JoinStep(i, j.table, j.kind, prev, rows, key, unique, multiplies, fan, note))
        prev = rows
    return steps