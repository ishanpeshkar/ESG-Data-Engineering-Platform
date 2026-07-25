# File: src/dashboard/app.py

import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path

GOLD_DB_PATH = Path("data/gold/esg_gold.duckdb")

st.set_page_config(
    page_title="ESG Data Platform — Assessment Dashboard",
    layout="wide",
)


@st.cache_data(ttl=30)  # cache for 30s so repeated reruns don't hammer DuckDB
def load_gold_data():
    con = duckdb.connect(str(GOLD_DB_PATH), read_only=True)
    valid_df = con.execute("SELECT * FROM gold_valid_records").fetchdf()
    flagged_df = con.execute("SELECT * FROM gold_flagged_records").fetchdf()
    con.close()
    return valid_df, flagged_df


st.title("🌱 ESG Data Platform — Assessment Dashboard")
st.caption("Bronze → Silver → Gold pipeline output, orchestrated via Airflow")

valid_df, flagged_df = load_gold_data()

total_docs = len(valid_df) + len(flagged_df)
valid_count = len(valid_df)
flagged_count = len(flagged_df)
pass_rate = (valid_count / total_docs * 100) if total_docs > 0 else 0

# ---- Summary metrics ----
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Documents Processed", total_docs)
col2.metric("Valid Records", valid_count)
col3.metric("Flagged Records", flagged_count)
col4.metric("Pass Rate", f"{pass_rate:.1f}%")

st.divider()

# ---- Tabs for valid vs flagged ----
tab1, tab2 = st.tabs(["🚩 Flagged Records", "✅ Valid Records"])

with tab1:
    st.subheader("Documents flagged for review")
    if flagged_count == 0:
        st.success("No flagged records.")
    else:
        st.warning(f"{flagged_count} document(s) require manual review.")

        # Let user filter by flag reason type
        all_reasons = flagged_df["_flags"].str.split("; ").explode().unique()
        selected_reason = st.selectbox(
            "Filter by flag reason",
            options=["All"] + sorted(all_reasons.tolist())
        )

        display_df = flagged_df
        if selected_reason != "All":
            display_df = flagged_df[flagged_df["_flags"].str.contains(selected_reason, na=False)]

        st.dataframe(
            display_df[["_source_file", "product_name", "gwp_total", "standard_reference", "_flags"]],
            use_container_width=True,
            hide_index=True,
        )

with tab2:
    st.subheader("Validated documents")
    if valid_count == 0:
        st.info("No valid records yet — all current documents are flagged for review.")
    else:
        st.dataframe(
            valid_df[["_source_file", "product_name", "gwp_total", "standard_reference"]],
            use_container_width=True,
            hide_index=True,
        )

st.divider()
st.caption(f"Data source: `{GOLD_DB_PATH}` | Refresh the page to reload latest pipeline output")