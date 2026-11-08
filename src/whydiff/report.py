"""Turn an attribution result into a report: summary sentence, waterfall data, row trails."""
from __future__ import annotations

from dataclasses import asdict

from .attribution import attribute
from .diagnostics import row_count_trail
from .evaluator import Evaluator

OFFSET_RATIO = 10.0
EPS = 1e-9


def _n(x):
    return f"{x:,.2f}"


def _gross(res):
    return sum(abs(c["effect"]) for c in res["causes"])


def is_offsetting(res, ratio=OFFSET_RATIO) -> bool:
    """True when causes cancel: gross effect is far larger than the gap."""
    gross, gap = _gross(res), abs(res["gap"])
    return gross > EPS and (gap < EPS or gross / gap > ratio)


def summarize(res) -> str:
    a, b, gap, causes = res["result_a"], res["result_b"], res["gap"], res["causes"]
    head = f"Query A = {_n(a)}, Query B = {_n(b)}."
    if abs(gap) < EPS:
        if not causes:
            return head + " The queries return the same value and no structural differences were found."
        return head + (f" The values match, but {len(causes)} structural difference(s) were "
                       "detected; their effects cancel or are zero.")
    if not causes:
        return head + f" Gap = {_n(gap)} with no structural difference detected, so all of it is unexplained."
    if is_offsetting(res):
        parts = "; ".join(f"{c['description']}: {c['effect']:+,.2f}" for c in causes)
        return (head + f" Gap = {_n(gap)}, but the detected causes largely cancel out (gross effect "
                f"{_n(_gross(res))}), so percent shares are not meaningful. Effects: {parts}.")
    parts = ", ".join(f"{c['share_pct']:.0f}% {c['description']}" for c in causes)
    tail = (f", {100 * res['residual'] / gap:.0f}% unexplained" if abs(res["residual"]) > EPS
            else " (no unexplained residual)")
    return head + f" Gap = {_n(gap)}: {parts}{tail}."


def waterfall_steps(res) -> list:
    steps = [{"label": "Query A", "measure": "absolute", "value": res["result_a"]}]
    steps += [{"label": f"{c['id']}: {c['kind']}", "measure": "relative", "value": c["effect"]}
              for c in res["causes"]]
    if abs(res["residual"]) > EPS:
        steps.append({"label": "Unexplained", "measure": "relative", "value": res["residual"]})
    steps.append({"label": "Query B", "measure": "total", "value": res["result_b"]})
    return steps


def build_report(con, sql_a: str, sql_b: str, max_exact: int = 8) -> dict:
    ev = Evaluator(con, sql_a, sql_b)
    res = attribute(ev, max_exact=max_exact)
    return {"summary": summarize(res), "offsetting": is_offsetting(res), "attribution": res,
            "waterfall": waterfall_steps(res),
            "trail_a": [asdict(s) for s in row_count_trail(con, sql_a)],
            "trail_b": [asdict(s) for s in row_count_trail(con, sql_b)]}