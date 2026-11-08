"""Stage 7: Excel workbook and Tableau-ready CSV built from a report dict."""
from __future__ import annotations

import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

CSV_FIELDS = ["pair_id", "step_order", "cause", "kind", "effect", "share_pct", "description"]
TRAIL_FIELDS = ["step", "table", "join_kind", "rows_before", "rows_after",
                "key_column", "key_unique", "multiplies", "fan_out", "note"]
NUM = "#,##0.00"

def _r(x, d=4):
    """Round for export; adding 0.0 turns -0.0 into 0.0."""
    return None if x is None else round(x, d) + 0.0

def cause_rows(report: dict, pair_id: str) -> list:
    """One row per cause plus a residual row, in waterfall order."""
    res = report["attribution"]
    rows = [{
    "pair_id": pair_id,
    "step_order": i,
    "cause": c["id"],
    "kind": c["kind"],
    "effect": _r(c["effect"]),
    "share_pct": _r(c["share_pct"]),
    "description": c["description"],
} for i, c in enumerate(res["causes"], start=1)]
    rows.append({"pair_id": pair_id, "step_order": len(rows) + 1, "cause": "residual",
                 "kind": "RESIDUAL", "effect": _r(res["residual"]),
                 "share_pct": _r(res["residual_share_pct"]),
                 "description": "Not explained by detected differences"})
    return rows


def causes_csv_bytes(report: dict, pair_id: str = "custom") -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    w.writeheader()
    w.writerows(cause_rows(report, pair_id))
    return buf.getvalue().encode("utf-8")


def _header(ws, labels):
    ws.append(labels)
    for cell in ws[1]:
        cell.font = Font(bold=True)


def _widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def excel_bytes(report: dict, sql_a: str, sql_b: str, pair_id: str = "custom") -> bytes:
    res = report["attribution"]
    wb = Workbook()

    ws = wb.active
    ws.title = "Summary"
    _header(ws, ["Metric", "Value"])
    items = [("Pair", pair_id), ("Query A result", res["result_a"]),
             ("Query B result", res["result_b"]), ("Gap (B minus A)", res["gap"]),
             ("Residual (unexplained)", res["residual"]),
             ("Residual share of gap (%)", res["residual_share_pct"]),
             ("Method", res["method"]), ("Patched queries run", res["evaluations"]),
             ("Runtime (seconds)", round(res["runtime_s"], 4)),
             ("Identity error", res["identity_error"]),
             ("Causes largely cancel", "yes" if report["offsetting"] else "no"),
             ("Summary", report["summary"])]
    for label, value in items:
        ws.append([label, value])
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=2):
        row[0].alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
        if isinstance(row[0].value, float):
            row[0].number_format = NUM
    _widths(ws, [30, 90])

    wc = wb.create_sheet("Causes")
    _header(wc, ["Pair", "Order", "Cause", "Kind", "Effect", "Share of gap (%)", "Description"])
    for r in cause_rows(report, pair_id):
        wc.append([r["pair_id"], r["step_order"], r["cause"], r["kind"], r["effect"],
                   r["share_pct"], r["description"]])
    for row in wc.iter_rows(min_row=2, min_col=5, max_col=6):
        for cell in row:
            cell.number_format = NUM
    _widths(wc, [10, 8, 10, 18, 16, 16, 90])

    wt = wb.create_sheet("RowTrail")
    _header(wt, ["Query"] + TRAIL_FIELDS)
    for label, trail in (("A", report["trail_a"]), ("B", report["trail_b"])):
        for s in trail:
            wt.append([label] + [s.get(f) for f in TRAIL_FIELDS])
    _widths(wt, [8, 6, 22, 12, 14, 14, 16, 12, 12, 10, 90])

    wq = wb.create_sheet("Queries")
    _header(wq, ["Query A", "Query B"])
    wq.append([sql_a, sql_b])
    for cell in wq[2]:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    wq.row_dimensions[2].height = 260
    _widths(wq, [70, 70])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()