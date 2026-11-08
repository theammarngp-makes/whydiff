import csv
import io

from openpyxl import load_workbook

from whydiff.exporters import CSV_FIELDS, cause_rows, causes_csv_bytes, excel_bytes


def fake_report():
    trail = [{"step": 0, "table": "orders", "join_kind": "BASE", "rows_before": 3,
              "rows_after": 3, "key_column": None, "key_unique": None,
              "multiplies": False, "fan_out": False, "note": "Starting rows"},
             {"step": 1, "table": "pay", "join_kind": "INNER", "rows_before": 3,
              "rows_after": 4, "key_column": "order_id", "key_unique": False,
              "multiplies": True, "fan_out": True, "note": "Rows rose"}]
    res = {"result_a": 100.0, "result_b": 70.0, "gap": -30.0, "method": "exact",
           "causes": [{"id": "c1", "kind": "JOIN_DIFF", "description": "extra join",
                       "effect": -20.0, "share_pct": 66.7},
                      {"id": "c2", "kind": "FILTER_DIFF", "description": "status filter",
                       "effect": -10.0, "share_pct": 33.3}],
           "residual": 0.0, "residual_share_pct": 0.0, "identity_error": 0.0,
           "evaluations": 4, "runtime_s": 0.01}
    return {"summary": "Query A = 100.00, Query B = 70.00.", "offsetting": False,
            "attribution": res, "waterfall": [], "trail_a": trail, "trail_b": trail[:1]}


def test_cause_rows_end_with_residual():
    rows = cause_rows(fake_report(), "P99")
    assert [r["cause"] for r in rows] == ["c1", "c2", "residual"]
    assert rows[-1]["kind"] == "RESIDUAL" and rows[0]["step_order"] == 1


def test_csv_has_spec_columns_and_values():
    text = causes_csv_bytes(fake_report(), "P99").decode("utf-8")
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert list(parsed[0].keys()) == CSV_FIELDS
    assert parsed[0]["pair_id"] == "P99" and float(parsed[0]["effect"]) == -20.0


def test_excel_has_four_sheets_with_content():
    data = excel_bytes(fake_report(), "SELECT 1", "SELECT 2", "P99")
    wb = load_workbook(io.BytesIO(data))
    assert wb.sheetnames == ["Summary", "Causes", "RowTrail", "Queries"]
    assert wb["Causes"].max_row == 4          # header + 2 causes + residual
    assert wb["RowTrail"].max_row == 4        # header + 2 rows for A + 1 row for B
    assert wb["Queries"]["A2"].value == "SELECT 1" and wb["Queries"]["B2"].value == "SELECT 2"
    labels = [c.value for c in wb["Summary"]["A"]]
    assert "Gap (B minus A)" in labels

def test_export_rounds_and_removes_negative_zero():
    rep = fake_report()
    rep["attribution"]["causes"][0]["effect"] = -35240.08000000229
    rep["attribution"]["residual"] = -0.0
    rep["attribution"]["residual_share_pct"] = -0.0
    rows = cause_rows(rep, "P99")
    assert rows[0]["effect"] == -35240.08
    assert str(rows[-1]["effect"]) == "0.0" and str(rows[-1]["share_pct"]) == "0.0"    