"""Scoring helpers for the benchmark (kept out of the script so they can be unit tested)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .attribution import sequential_attribution

# Planted causes by construction, taken from the benchmark design table (brief, Section 10).
# They describe what was planted in each pair, not what the tool reports.
PLANTED = {
    "P01": ["FILTER_DIFF"],
    "P02": ["JOIN_DIFF"],
    "P03": ["AGG_EXPR_DIFF"],
    "P04": ["JOIN_DIFF", "JOIN_DIFF", "AGG_EXPR_DIFF"],
    "P05": ["JOIN_DIFF"],
    "P06": ["JOIN_TYPE_DIFF"],
    "P07": ["TIME_DIFF"],
    "P08": ["DISTINCT_DIFF"],
    "P09": ["JOIN_DIFF", "FILTER_DIFF"],
    "P10": ["FILTER_DIFF", "AGG_EXPR_DIFF"],
    "P11": ["JOIN_DIFF", "FILTER_DIFF", "TIME_DIFF"],
    "P12": ["DISTINCT_DIFF"],
    "P13": ["AGG_EXPR_DIFF"],
    "P14": [],
    "P15": ["AGG_EXPR_DIFF", "TIME_DIFF"],
    "P16": ["JOIN_DIFF", "FILTER_DIFF", "AGG_EXPR_DIFF", "TIME_DIFF"],
}



def score_causes(planted, causes):
    """Match planted kinds to the underlying differences inside reported causes.
    A COMBINED cause holds several differences, so it can match several planted kinds,
    but each member difference is used at most once.
    Returns (matched, recall, precision); a ratio is None when its denominator is 0.
    Precision = reported causes that matched at least one planted kind."""
    pools = [[m.kind for m in c.members] for c in causes]
    used, hit = set(), 0
    for kind in planted:
        for i, kinds in enumerate(pools):
            if kind in kinds:
                kinds.remove(kind)
                used.add(i)
                hit += 1
                break
    recall = hit / len(planted) if planted else None
    precision = len(used) / len(pools) if pools else None
    return hit, recall, precision

def order_spread_pct(ev, effects):
    """How much a simple one-at-a-time attribution depends on order.
    Compares forward and reverse orderings; returns the largest difference for any
    cause as a percent of the total absolute effect. None for fewer than 2 causes.
    (Every subset it needs was already evaluated by the exact Shapley run.)"""
    ids = [c.id for c in ev.causes]
    gross = sum(abs(x) for x in effects.values())
    if len(ids) < 2 or gross == 0:
        return None
    fwd = sequential_attribution(ids, ev.v)
    rev = sequential_attribution(ids[::-1], ev.v)
    return 100.0 * max(abs(fwd[i] - rev[i]) for i in ids) / gross

def load_planted(pair_dir) -> list:
    """Planted cause kinds for one pair, read from its manifest.yaml."""
    data = yaml.safe_load((Path(pair_dir) / "manifest.yaml").read_text())
    return list(data.get("planted_causes") or [])