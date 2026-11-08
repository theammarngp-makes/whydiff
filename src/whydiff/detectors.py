"""Compare two QueryProfiles and list the structural differences."""
from __future__ import annotations

from dataclasses import dataclass, field

from .profile import QueryProfile, UnsupportedConstruct

FILTER_DIFF = "FILTER_DIFF"
JOIN_DIFF = "JOIN_DIFF"
JOIN_TYPE_DIFF = "JOIN_TYPE_DIFF"
AGG_EXPR_DIFF = "AGG_EXPR_DIFF"
DISTINCT_DIFF = "DISTINCT_DIFF"
TIME_DIFF = "TIME_DIFF"


@dataclass(frozen=True)
class Difference:
    id: str
    kind: str
    description: str
    # data the Stage 3 patchers will need; not part of equality or hashing
    payload: dict = field(default_factory=dict, compare=False)


def detect_filters(a: QueryProfile, b: QueryProfile):
    out = []
    for p in sorted(set(a.predicates) - set(b.predicates)):
        out.append((FILTER_DIFF, f"Filter only in query A: {p}",
                    {"side": "A_only", "predicate": p}))
    for p in sorted(set(b.predicates) - set(a.predicates)):
        out.append((FILTER_DIFF, f"Filter only in query B: {p}",
                    {"side": "B_only", "predicate": p}))
    return out


def detect_joins(a: QueryProfile, b: QueryProfile):
    if a.base_table != b.base_table:
        raise UnsupportedConstruct("the queries start FROM different tables")
    ja = {j.table: j for j in a.joins}
    jb = {j.table: j for j in b.joins}
    out = []
    for t in sorted(set(ja) - set(jb)):
        out.append((JOIN_DIFF, f"Join to {t} only in query A (fan-out candidate)",
                    {"side": "A_only", "table": t, "join_kind": ja[t].kind, "on": ja[t].on}))
    for t in sorted(set(jb) - set(ja)):
        out.append((JOIN_DIFF, f"Join to {t} only in query B",
                    {"side": "B_only", "table": t, "join_kind": jb[t].kind, "on": jb[t].on}))
    for t in sorted(set(ja) & set(jb)):
        if ja[t].on != jb[t].on:
            raise UnsupportedConstruct(f"the ON condition for {t} differs")
        if ja[t].kind != jb[t].kind:
            out.append((JOIN_TYPE_DIFF, f"Join to {t} is {ja[t].kind} in A but {jb[t].kind} in B",
                        {"table": t, "a_kind": ja[t].kind, "b_kind": jb[t].kind}))
    return out


def detect_time(a: QueryProfile, b: QueryProfile):
    if set(a.time_predicates) == set(b.time_predicates):
        return []
    return [(TIME_DIFF, "Date/time conditions differ between the queries",
             {"a_predicates": a.time_predicates, "b_predicates": b.time_predicates})]


def detect_metric(a: QueryProfile, b: QueryProfile):
    if a.metric == b.metric:
        return []
    sa, sb = a.single_agg, b.single_agg
    payload = {"a_metric": a.metric, "b_metric": b.metric}
    if sa and sb and sa.func == sb.func:
        flag_differs = sa.distinct != sb.distinct and (sa.func == "count" or sa.arg == sb.arg)
        both_distinct_count = sa.distinct and sb.distinct and sa.func == "count"
        if flag_differs or both_distinct_count:
            return [(DISTINCT_DIFF, f"What is counted differs: {a.metric} vs {b.metric}", payload)]
    return [(AGG_EXPR_DIFF, f"Aggregate expression differs: {a.metric} vs {b.metric}", payload)]


def diff_profiles(a: QueryProfile, b: QueryProfile) -> list:
    if a.group_by != b.group_by:
        raise UnsupportedConstruct("the GROUP BY columns differ")
    found = (detect_joins(a, b) + detect_filters(a, b)
             + detect_metric(a, b) + detect_time(a, b))
    return [Difference(f"d{i}", kind, desc, payload)
            for i, (kind, desc, payload) in enumerate(found, start=1)]