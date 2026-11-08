"""Counterfactual evaluator: v(S) = result of query A with the causes in S patched in."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .detectors import (AGG_EXPR_DIFF, DISTINCT_DIFF, FILTER_DIFF, JOIN_DIFF,
                        TIME_DIFF, diff_profiles)
from .patchers import apply_patches
from .profile import build_profile
from .runner import run_sql


class EvaluationError(Exception):
    """A patched query failed to run."""


@dataclass(frozen=True)
class Cause:
    id: str
    kind: str          # a detector kind, or COMBINED for bundled differences
    description: str
    members: tuple     # the Difference objects patched together


def _refs(texts, tables) -> set:
    return {t for t in tables if any(re.search(rf"\b{re.escape(t)}\.", x) for x in texts)}


def _a_text(d) -> list:
    p = d.payload
    if d.kind == FILTER_DIFF and p["side"] == "A_only":
        return [p["predicate"]]
    if d.kind == TIME_DIFF:
        return p["a_predicates"]
    if d.kind in (AGG_EXPR_DIFF, DISTINCT_DIFF):
        return [p["a_metric"]]
    return []


def _b_text(d) -> list:
    p = d.payload
    if d.kind == FILTER_DIFF and p["side"] == "B_only":
        return [p["predicate"]]
    if d.kind == TIME_DIFF:
        return p["b_predicates"]
    if d.kind in (AGG_EXPR_DIFF, DISTINCT_DIFF):
        return [p["b_metric"]]
    return []


def bundle_differences(diffs, pa, pb) -> list:
    """Merge differences that cannot be applied alone (e.g. dropping a join that the
    aggregate still uses). Independent differences stay separate causes."""
    a_tables = {pa.base_table} | {j.table for j in pa.joins}
    universe = a_tables | {pb.base_table} | {j.table for j in pb.joins}
    parent = {d.id: d.id for d in diffs}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for j in (d for d in diffs if d.kind == JOIN_DIFF and d.payload["side"] == "A_only"):
        for x in diffs:
            if x is not j and j.payload["table"] in _refs(_a_text(x), universe):
                union(j.id, x.id)          # x removes the references j's table needs
    adders = {d.payload["table"]: d for d in diffs
              if d.kind == JOIN_DIFF and d.payload["side"] == "B_only"}
    for x in diffs:
        for t in _refs(_b_text(x), universe) - a_tables:
            if t in adders:
                union(x.id, adders[t].id)  # x uses a table only B joins

    groups: dict = {}
    for d in diffs:
        groups.setdefault(find(d.id), []).append(d)
    causes = []
    for i, members in enumerate(sorted(groups.values(), key=lambda g: g[0].id), start=1):
        if len(members) == 1:
            m = members[0]
            causes.append(Cause(f"c{i}", m.kind, m.description, (m,)))
        else:
            desc = "Combined change: " + "; ".join(m.description for m in members)
            causes.append(Cause(f"c{i}", "COMBINED", desc, tuple(members)))
    return causes


class Evaluator:
    def __init__(self, con, sql_a: str, sql_b: str):
        self.con, self.sql_a, self.sql_b = con, sql_a, sql_b
        self.pa, self.pb = build_profile(sql_a), build_profile(sql_b)
        self.diffs = diff_profiles(self.pa, self.pb)
        self.causes = bundle_differences(self.diffs, self.pa, self.pb)
        self.sql_log: dict = {}
        self._cache: dict = {}
        self.result_a = self.v(frozenset())
        self.result_b = run_sql(con, sql_b)

    @property
    def all_ids(self) -> frozenset:
        return frozenset(c.id for c in self.causes)

    @property
    def n_evaluations(self) -> int:
        """Number of distinct subsets actually executed (cache hits not counted)."""
        return len(self._cache)

    def sql_for(self, subset) -> str:
        if not subset:
            return self.sql_a
        members = [m for c in self.causes if c.id in subset for m in c.members]
        return apply_patches(self.pa, self.pb, members)

    def v(self, subset) -> float:
        key = frozenset(subset)
        if key not in self._cache:
            sql = self.sql_for(key)
            try:
                self._cache[key] = run_sql(self.con, sql)
            except Exception as e:  # report the SQL so the failure can be debugged
                raise EvaluationError(f"patched query failed ({e}):\n{sql}") from e
            self.sql_log[key] = sql
        return self._cache[key]

    def shortfall(self) -> float:
        """B minus the fully patched A: what the detected differences do not explain."""
        return self.result_b - self.v(self.all_ids)