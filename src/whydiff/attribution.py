"""Shapley attribution of the gap between query A and query B to its causes."""
from __future__ import annotations

import random
import time
from itertools import combinations
from math import factorial


class AttributionError(Exception):
    """The attribution failed its own consistency check."""


def shapley_exact(players, v) -> dict:
    """Exact Shapley values. v maps a frozenset of players to a number."""
    n = len(players)
    phi = {p: 0.0 for p in players}
    for p in players:
        others = [q for q in players if q != p]
        for r in range(n):
            weight = factorial(r) * factorial(n - r - 1) / factorial(n)
            for s in combinations(others, r):
                s = frozenset(s)
                phi[p] += weight * (v(s | {p}) - v(s))
    return phi


def shapley_monte_carlo(players, v, n_perm: int = 200, seed: int = 0) -> dict:
    """Estimate Shapley values by averaging marginal gains over random orderings.
    Each ordering's gains add up to v(all) - v(empty), so the total is still exact."""
    rng = random.Random(seed)
    phi = {p: 0.0 for p in players}
    for _ in range(n_perm):
        order = list(players)
        rng.shuffle(order)
        prefix, prev = frozenset(), v(frozenset())
        for p in order:
            prefix = prefix | {p}
            cur = v(prefix)
            phi[p] += cur - prev
            prev = cur
    return {p: x / n_perm for p, x in phi.items()}


def sequential_attribution(order, v) -> dict:
    """Order-dependent attribution: apply causes one at a time in the given order."""
    out, prefix, prev = {}, frozenset(), v(frozenset())
    for p in order:
        prefix = prefix | {p}
        cur = v(prefix)
        out[p] = cur - prev
        prev = cur
    return out


def attribute(ev, max_exact: int = 8, n_perm: int = 200, seed: int = 0) -> dict:
    """Attribute B - A to the causes found by an Evaluator. Returns a plain dict."""
    t0 = time.perf_counter()
    ids = [c.id for c in ev.causes]
    a, b = ev.result_a, ev.result_b
    gap = b - a
    if len(ids) <= max_exact:
        method, phi = "exact", shapley_exact(ids, ev.v)
    else:
        method, phi = "estimated", shapley_monte_carlo(ids, ev.v, n_perm, seed)
    residual = b - ev.v(ev.all_ids)
    error = abs(sum(phi.values()) + residual - gap)
    if error > 1e-6 * max(1.0, abs(a), abs(b)):
        raise AttributionError(f"identity check failed: error {error}")

    def share(x):
        return None if abs(gap) < 1e-9 else 100.0 * x / gap

    rows = [{"id": c.id, "kind": c.kind, "description": c.description,
             "members": [m.id for m in c.members],
             "effect": phi[c.id], "share_pct": share(phi[c.id])} for c in ev.causes]
    return {"result_a": a, "result_b": b, "gap": gap, "method": method,
            "n_perm": n_perm if method == "estimated" else None,
            "causes": rows, "residual": residual, "residual_share_pct": share(residual),
            "identity_error": error, "identity_ok": True,
            "evaluations": ev.n_evaluations, "runtime_s": time.perf_counter() - t0}