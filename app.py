"""Stage 6: WhyDiff Streamlit app. Run with: streamlit run app.py"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from whydiff.attribution import AttributionError  # noqa: E402
from whydiff.evaluator import EvaluationError  # noqa: E402
from whydiff.exporters import causes_csv_bytes, excel_bytes  # noqa: E402
from whydiff.profile import UnsupportedConstruct  # noqa: E402
from whydiff.report import build_report  # noqa: E402

DB = ROOT / "data" / "olist.duckdb"
PAIRS = ROOT / "benchmark" / "pairs"

st.set_page_config(page_title="WhyDiff", layout="wide")


@st.cache_resource
def get_con():
    return duckdb.connect(str(DB), read_only=True)


def pair_ids():
    return sorted(p.name for p in PAIRS.iterdir() if p.is_dir() and p.name.startswith("P"))


def load_pair(pid):
    d = PAIRS / pid
    return (d / "query_a.sql").read_text(), (d / "query_b.sql").read_text()


def load_sample():
    st.session_state["qa"], st.session_state["qb"] = load_pair(st.session_state["sample"])
    st.session_state.pop("report", None)
    st.session_state.pop("error", None)


def waterfall_figure(steps):
    level, levels = 0.0, []
    for s in steps:
        level = s["value"] if s["measure"] != "relative" else level + s["value"]
        levels.append(level)
    lo, hi = min(levels), max(levels)
    pad = max((hi - lo) * 0.25, abs(hi) * 0.002, 1.0)
    fig = go.Figure(go.Waterfall(orientation="v", measure=[s["measure"] for s in steps],
                                 x=[s["label"] for s in steps], y=[s["value"] for s in steps]))
    fig.update_yaxes(range=[lo - pad, hi + pad])
    fig.update_layout(title="From query A to query B (axis zoomed to the gap)", showlegend=False)
    return fig

def pair_label(qa, qb):
    """Sample pair id if the queries are unchanged, otherwise 'custom'."""
    try:
        sa, sb = load_pair(st.session_state.get("sample"))
    except Exception:
        return "custom"
    norm = lambda s: " ".join(s.split())
    same = (norm(qa), norm(qb)) == (norm(sa), norm(sb))
    return st.session_state["sample"] if same else "custom"
    
TRAIL_COLS = ["step", "table", "join_kind", "rows_before", "rows_after",
              "key_column", "key_unique", "fan_out", "note"]

st.title("WhyDiff")
st.caption("Why do two SQL queries for the same metric disagree? Run both, find the "
           "differences, and attribute the gap to causes.")

if not DB.exists():
    st.error(f"Database not found: {DB}. Run scripts/load_data.py first.")
    st.stop()
con = get_con()
ids = pair_ids()
if "qa" not in st.session_state:
    st.session_state["sample"] = "P11" if "P11" in ids else ids[0]
    load_sample()

with st.sidebar:
    st.header("Settings")
    st.success("Olist database connected")
    st.selectbox("Sample pair", ids, key="sample")
    st.button("Load sample", on_click=load_sample)
    max_exact = st.slider("Exact Shapley up to this many causes", 2, 10, 8,
                          help="n causes need 2^n query runs. Above this, a sampled estimate is used.")

left, right = st.columns(2)
left.text_area("Query A", key="qa", height=240)
right.text_area("Query B", key="qb", height=240)

if st.button("Run WhyDiff", type="primary"):
    try:
        st.session_state["report"] = build_report(con, st.session_state["qa"],
                                                  st.session_state["qb"], max_exact)
        st.session_state["report_sql"] = (st.session_state["qa"], st.session_state["qb"])
        st.session_state["report_pair"] = pair_label(*st.session_state["report_sql"])
        st.session_state.pop("error", None)
    except UnsupportedConstruct as e:
        st.session_state.pop("report", None)
        st.session_state["error"] = f"Unsupported SQL in version 1: {e}"
    except (EvaluationError, AttributionError) as e:
        st.session_state.pop("report", None)
        st.session_state["error"] = f"Could not complete the analysis: {str(e).splitlines()[0]}"
    except Exception as e:  # keep stack traces out of the UI
        st.session_state.pop("report", None)
        st.session_state["error"] = f"Could not run these queries ({type(e).__name__})."

if "error" in st.session_state:
    st.error(st.session_state["error"])

rep = st.session_state.get("report")
if rep:
    res = rep["attribution"]
    st.subheader("Result")
    st.success(rep["summary"])
    if rep["offsetting"]:
        st.warning("The causes largely cancel out, so read the effects, not the percent shares.")
    rows = [{"Cause": c["id"], "Kind": c["kind"], "Description": c["description"],
             "Effect": round(c["effect"], 2),
             "Share of gap (%)": None if c["share_pct"] is None else round(c["share_pct"], 1)}
            for c in res["causes"]]
    rs = res["residual_share_pct"]
    rows.append({"Cause": "-", "Kind": "RESIDUAL", "Description": "Not explained by detected differences",
                 "Effect": round(res["residual"], 2),
                 "Share of gap (%)": None if rs is None else round(rs, 1)})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption(f"{res['method'].capitalize()} Shapley, {res['evaluations']} patched queries run in "
               f"{res['runtime_s']:.2f}s, identity error {res['identity_error']:.1e}.")
    qa_run, qb_run = st.session_state["report_sql"]
    pid = st.session_state["report_pair"]
    d1, d2 = st.columns(2)
    d1.download_button("Download Excel report", data=excel_bytes(rep, qa_run, qb_run, pid),
                       file_name=f"whydiff_{pid}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    d2.download_button("Download Tableau CSV", data=causes_csv_bytes(rep, pid),
                       file_name=f"whydiff_{pid}_causes.csv", mime="text/csv")
    st.plotly_chart(waterfall_figure(rep["waterfall"]))
    st.subheader("Row-count trail (rows after each join, before WHERE filters)")
    ta, tb = st.columns(2)
    ta.write("Query A")
    ta.dataframe(pd.DataFrame(rep["trail_a"])[TRAIL_COLS], hide_index=True)
    tb.write("Query B")
    tb.dataframe(pd.DataFrame(rep["trail_b"])[TRAIL_COLS], hide_index=True)