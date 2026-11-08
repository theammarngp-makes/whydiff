"""Parse a SQL query into a QueryProfile (the facts the detectors compare)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

TIME_COL = re.compile(r"timestamp|date|_at$")  # heuristic: column name looks like a time


class UnsupportedConstruct(Exception):
    """Raised when a query uses SQL that version 1 does not support."""


@dataclass
class JoinInfo:
    table: str
    alias: str
    kind: str  # INNER, LEFT, RIGHT, FULL, CROSS
    on: str


@dataclass
class AggInfo:
    func: str
    arg: str
    distinct: bool


@dataclass
class QueryProfile:
    sql: str
    ast: exp.Expression = field(repr=False)
    base_table: str = ""
    joins: list = field(default_factory=list)
    predicates: list = field(default_factory=list)  # non-time filters (incl. semi-joins)
    time_predicates: list = field(default_factory=list)
    metric: str = ""
    single_agg: AggInfo | None = None
    group_by: list = field(default_factory=list)


def _arg(node, name):
    """sqlglot renamed 'from'/'with' to 'from_'/'with_' in newer versions."""
    return node.args.get(name) or node.args.get(name + "_")


def _norm(node, alias_map: dict, single: str | None) -> str:
    """Normalised text: aliases replaced by real table names, identifiers lowercased."""
    if isinstance(node, exp.Star):
        return "*"
    n = node.copy()
    for col in n.find_all(exp.Column):
        t = col.table
        if t in alias_map:
            col.set("table", exp.to_identifier(alias_map[t]))
        elif not t and single:
            col.set("table", exp.to_identifier(single))
    return n.sql(dialect="duckdb", normalize=True)


def _flatten_and(node):
    if isinstance(node, exp.Paren):
        return _flatten_and(node.this)
    if isinstance(node, exp.And):
        return _flatten_and(node.this) + _flatten_and(node.expression)
    return [node]


def _tables_of(select: exp.Select, ctes: dict) -> dict:
    """alias -> real table name for the FROM table and plain joined tables."""
    frm = _arg(select, "from")
    if frm is None or not isinstance(frm.this, exp.Table):
        raise UnsupportedConstruct("FROM must be a plain table")
    if frm.this.name in ctes:
        raise UnsupportedConstruct("FROM a CTE is not supported")
    out = {frm.this.alias_or_name: frm.this.name}
    for j in select.args.get("joins") or []:
        if isinstance(j.this, exp.Table) and j.this.name not in ctes:
            out[j.this.alias_or_name] = j.this.name
    return out


def _norm_select(select, ctes: dict) -> str:
    """Normalised text of an inner SELECT; rejects correlated subqueries."""
    if not isinstance(select, exp.Select):
        raise UnsupportedConstruct("only plain SELECT subqueries are supported")
    amap = _tables_of(select, ctes)
    for col in select.find_all(exp.Column):
        if col.table and col.table not in amap:
            raise UnsupportedConstruct("correlated subquery")
    single = next(iter(amap.values())) if len(amap) == 1 else None
    return _norm(select, amap, single)


def _semi_from_join(j, ctes, amap, single) -> str:
    """JOIN to a CTE/derived table that is just a key list -> semi-join predicate text."""
    if isinstance(j.this, exp.Subquery):
        alias, body = j.this.alias, j.this.this
    else:
        alias, body = j.this.alias_or_name, ctes[j.this.name]
    ok = (isinstance(body, exp.Select) and len(body.expressions) == 1
          and not body.args.get("group") and not body.find(exp.AggFunc)
          and isinstance(j.args.get("on"), exp.EQ))
    if not ok:
        raise UnsupportedConstruct("JOIN to a CTE/subquery that is not a simple key list")
    eq = j.args["on"]
    sides = [eq.this, eq.expression]
    mine = [s for s in sides if isinstance(s, exp.Column) and s.table == alias]
    other = [s for s in sides if isinstance(s, exp.Column) and s.table != alias]
    if len(mine) != 1 or len(other) != 1:
        raise UnsupportedConstruct("JOIN to a CTE/subquery with a complex ON")
    return f"{_norm(other[0], amap, single)} in ({_norm_select(body, {})})"


def build_profile(sql: str) -> QueryProfile:
    try:
        trees = [t for t in sqlglot.parse(sql, read="duckdb") if t is not None]
    except SqlglotError as e:
        raise UnsupportedConstruct(f"cannot parse SQL: {str(e)[:120]}")
    if len(trees) != 1:
        raise UnsupportedConstruct("exactly one SQL statement is expected")
    tree = trees[0]
    if not isinstance(tree, exp.Select):
        raise UnsupportedConstruct(f"{type(tree).__name__} is not a plain SELECT")
    if tree.find(exp.Window):
        raise UnsupportedConstruct("window function")
    with_ = _arg(tree, "with")
    if with_ is not None and with_.args.get("recursive"):
        raise UnsupportedConstruct("recursive CTE")
    ctes = {c.alias: c.this for c in with_.expressions} if with_ is not None else {}

    amap = _tables_of(tree, ctes)
    single = next(iter(amap.values())) if len(amap) == 1 else None
    prof = QueryProfile(sql=sql, ast=tree, base_table=_arg(tree, "from").this.name)

    semis = []
    for j in tree.args.get("joins") or []:
        if j.args.get("using"):
            raise UnsupportedConstruct("JOIN ... USING")
        is_cte = isinstance(j.this, exp.Table) and j.this.name in ctes
        if isinstance(j.this, exp.Subquery) or is_cte:
            semis.append(_semi_from_join(j, ctes, amap, single))
            continue
        side = (j.side or "").upper()
        kind = side or ("CROSS" if (j.kind or "").upper() == "CROSS" else "INNER")
        on = _norm(j.args["on"], amap, None) if j.args.get("on") is not None else ""
        if any(x.table == j.this.name for x in prof.joins) or j.this.name == prof.base_table:
            raise UnsupportedConstruct(f"table {j.this.name} used more than once")
        prof.joins.append(JoinInfo(j.this.name, j.this.alias_or_name, kind, on))

    where = _arg(tree, "where")
    conds = _flatten_and(where.this) if where is not None else []
    for c in conds:
        if isinstance(c, exp.In) and isinstance(c.args.get("query"), (exp.Subquery, exp.Select)):
            q = c.args["query"]
            inner = q.this if isinstance(q, exp.Subquery) else q
            semis.append(f"{_norm(c.this, amap, single)} in ({_norm_select(inner, ctes)})")
        elif c.find(exp.Select):
            raise UnsupportedConstruct("subquery inside a WHERE condition")
        elif any(TIME_COL.search(col.name.lower()) for col in c.find_all(exp.Column)):
            prof.time_predicates.append(_norm(c, amap, single))
        else:
            prof.predicates.append(_norm(c, amap, single))
    prof.predicates += semis
    prof.predicates.sort()
    prof.time_predicates.sort()

    aggs = [e for e in tree.expressions if e.find(exp.AggFunc)]
    if len(aggs) != 1:
        raise UnsupportedConstruct("exactly one aggregate column is expected")
    proj = aggs[0].unalias()
    prof.metric = _norm(proj, amap, single)
    if isinstance(proj, exp.AggFunc) and proj.this is not None:
        inner = proj.this
        distinct = isinstance(inner, exp.Distinct)
        arg = (", ".join(_norm(x, amap, single) for x in inner.expressions)
               if distinct else _norm(inner, amap, single))
        prof.single_agg = AggInfo(proj.key, arg, distinct)
    grp = _arg(tree, "group")
    prof.group_by = sorted(_norm(g, amap, single) for g in grp.expressions) if grp else []
    return prof