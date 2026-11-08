"""Patch query A's syntax tree so it behaves like query B for chosen differences."""
from __future__ import annotations

from sqlglot import exp

from .detectors import (AGG_EXPR_DIFF, DISTINCT_DIFF, FILTER_DIFF, JOIN_DIFF,
                        JOIN_TYPE_DIFF, TIME_DIFF)
from .profile import UnsupportedConstruct, _arg, _flatten_and, _norm, _tables_of


def _alias_map(tree) -> dict:
    """alias -> real table name (same logic the profile used)."""
    w = _arg(tree, "with")
    ctes = {c.alias: c.this for c in w.expressions} if w is not None else {}
    return _tables_of(tree, ctes)


def _single(amap: dict):
    return next(iter(amap.values())) if len(amap) == 1 else None


class PatchContext:
    """Working copy of A plus what is needed to translate B's pieces into A's aliases."""

    def __init__(self, pa, pb):
        self.tree = pa.ast.copy()
        self.pb = pb
        self.a_alias = _alias_map(pa.ast)
        self.b_alias = _alias_map(pb.ast)
        self.a_single = _single(self.a_alias)
        self.b_single = _single(self.b_alias)
        self.dst = {t: a for a, t in self.a_alias.items()}  # table -> alias used in A


def _retarget(node, ctx):
    """Copy a piece of B, renaming B's table aliases to the aliases used in patched A."""
    n = node.copy()
    for col in n.find_all(exp.Column):
        if col.table in ctx.b_alias:
            real = ctx.b_alias[col.table]
            col.set("table", exp.to_identifier(ctx.dst.get(real, col.table)))
    return n


def _conjs(tree):
    w = _arg(tree, "where")
    return _flatten_and(w.this) if w is not None else []


def _set_where(tree, conds):
    tree.set("where", exp.Where(this=exp.and_(*conds)) if conds else None)


def _find_join(tree, table):
    for j in tree.args.get("joins") or []:
        if isinstance(j.this, exp.Table) and j.this.name == table:
            return j
    raise UnsupportedConstruct(f"cannot find the join to {table}")


def _patch_join(ctx, d):
    t = d.payload["table"]
    joins = list(ctx.tree.args.get("joins") or [])
    if d.payload["side"] == "A_only":
        gone = _find_join(ctx.tree, t)
        ctx.tree.set("joins", [j for j in joins if j is not gone] or None)
        ctx.dst.pop(t, None)
        return
    bj = _find_join(ctx.pb.ast, t)
    alias = bj.this.alias_or_name
    if alias in ctx.dst.values():
        raise UnsupportedConstruct(f"alias clash: {alias} is already used in query A")
    ctx.dst[t] = alias
    new = bj.copy()
    if new.args.get("on") is not None:
        new.set("on", _retarget(new.args["on"], ctx))
    ctx.tree.set("joins", joins + [new])


def _patch_join_type(ctx, d):
    mine = _find_join(ctx.tree, d.payload["table"])
    theirs = _find_join(ctx.pb.ast, d.payload["table"])
    mine.set("side", theirs.args.get("side"))
    mine.set("kind", theirs.args.get("kind"))


def _drop(ctx, texts):
    cs = _conjs(ctx.tree)
    keep = [c for c in cs if _norm(c, ctx.a_alias, ctx.a_single) not in texts]
    if len(keep) == len(cs):
        raise UnsupportedConstruct("cannot find the condition to remove "
                                   "(semi-join conditions are not patchable in v1)")
    _set_where(ctx.tree, keep)


def _add(ctx, texts):
    new = [_retarget(c, ctx) for c in _conjs(ctx.pb.ast)
           if _norm(c, ctx.b_alias, ctx.b_single) in texts]
    if not new:
        raise UnsupportedConstruct("cannot find the condition to add from query B")
    _set_where(ctx.tree, _conjs(ctx.tree) + new)


def _patch_filter(ctx, d):
    (_drop if d.payload["side"] == "A_only" else _add)(ctx, {d.payload["predicate"]})


def _patch_time(ctx, d):
    if d.payload["a_predicates"]:
        _drop(ctx, set(d.payload["a_predicates"]))
    if d.payload["b_predicates"]:
        _add(ctx, set(d.payload["b_predicates"]))


def _patch_metric(ctx, d):
    def agg_of(tree):
        return next(e for e in tree.expressions if e.find(exp.AggFunc))
    mine, theirs = agg_of(ctx.tree), agg_of(ctx.pb.ast)
    new = _retarget(theirs.unalias(), ctx)
    if isinstance(mine, exp.Alias):
        new = exp.alias_(new, mine.alias)
    ctx.tree.set("expressions", [new if e is mine else e for e in ctx.tree.expressions])


_PATCHERS = {JOIN_DIFF: _patch_join, JOIN_TYPE_DIFF: _patch_join_type,
             FILTER_DIFF: _patch_filter, TIME_DIFF: _patch_time,
             AGG_EXPR_DIFF: _patch_metric, DISTINCT_DIFF: _patch_metric}


def _rank(d) -> int:
    """Add joins first, then other edits, remove joins last."""
    if d.kind == JOIN_DIFF:
        return 0 if d.payload["side"] == "B_only" else 2
    return 1


def apply_patches(pa, pb, diffs) -> str:
    """SQL text of query A with the given differences patched to match B."""
    ctx = PatchContext(pa, pb)
    for d in sorted(diffs, key=lambda x: (_rank(x), x.id)):
        _PATCHERS[d.kind](ctx, d)
    return ctx.tree.sql(dialect="duckdb")