"""
app.py
CDPL ERP Flat-Glass Processing — Automated Reporting Dashboard
Enterprise Streamlit Application | Single-View Architecture
"""
from __future__ import annotations

import hashlib
import pandas as pd
import streamlit as st

from core.aggregation import build_pivot_df, build_unit_df, tag_order_status
from core.excel_exporter import export_to_excel
from core.ingestion import load_erp_excel
from components.two_tier_table import render_two_tier_table

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CDPL Glass Reporting",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Hide Streamlit default UI elements ─────────────────────────────────────
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Hides the "Deploy" button and the top right toolbar */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stHeader"] {display: none !important;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS overrides
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600; font-size: 14px; padding: 8px 20px;
        border-radius: 6px 6px 0 0;
    }
    div[data-testid="stDownloadButton"] button {
        background: #0EA5E9; color: white; border: none; border-radius: 6px;
        font-weight: 600; padding: 6px 16px; transition: all 0.2s ease-in-out;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background: #0284C7; color: white; border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 2.5rem 2rem; border-radius: 16px; color: white; margin-bottom: 2rem; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); border: 1px solid rgba(255,255,255,0.05);">
    <h1 style="margin: 0; font-size: 2.25rem; font-weight: 800; letter-spacing: -0.025em; display: flex; align-items: center; gap: 1rem; color: #f8fafc;">
        <span style="background: linear-gradient(135deg, #38bdf8, #0284c7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">CDPL</span> Glass Processing
    </h1>
    <div style="margin-top: 1rem; font-size: 0.95rem; color: #94a3b8; font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; display: flex; gap: 0.75rem; align-items: center;">
        <span>Architectural Flat-Glass</span>
        <span style="color: #475569;">•</span>
        <span>ERP Production Reporting</span>
        <span style="color: #475569;">•</span>
        <span style="color: #38bdf8;">Automated Pipeline</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# File Uploader + Data Processing
# ─────────────────────────────────────────────────────────────────────────────

with st.container(border=True):
    st.markdown("#### 📤 Upload Production Data")
    st.markdown("Upload your Raw Data")
    uploaded = st.file_uploader(
        "Select file",
        type=["xlsx"],
        label_visibility="collapsed"
    )


def _md5(file_obj) -> str:
    h = hashlib.md5(file_obj.read()).hexdigest()
    file_obj.seek(0)
    return h


def _process_file(file) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the full ingestion → unit → pivot pipeline."""
    raw_df    = load_erp_excel(file)
    unit_df   = build_unit_df(raw_df)
    pivot_df  = build_pivot_df(unit_df)
    return raw_df, unit_df, pivot_df


# Initialise or update session state on upload change
if uploaded:
    file_hash = _md5(uploaded)
    if st.session_state.get("upload_hash") != file_hash:
        with st.spinner("⏳ Processing ERP data…"):
            raw_df, unit_df, pivot_df = _process_file(uploaded)
            pivot_df = tag_order_status(pivot_df)
            
            st.session_state.update({
                "upload_hash":    file_hash,
                "pivot_df":       pivot_df,
                "is_demo":        False,
            })
        st.success(f"✅ Loaded {len(raw_df):,} ERP rows → {len(pivot_df):,} orders")
else:
    # Clear session state if file is removed
    if "upload_hash" in st.session_state and st.session_state["upload_hash"] is not None:
        st.session_state.pop("upload_hash", None)
        st.session_state.pop("pivot_df", None)

# Safely get pivot_df
if "pivot_df" in st.session_state:
    pivot_df = tag_order_status(st.session_state["pivot_df"].copy())
else:
    pivot_df = pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard View
# ─────────────────────────────────────────────────────────────────────────────

# ── Controls row ──────────────────────────────────────────────────────────
ctrl_col1, ctrl_col2 = st.columns([3, 1])
with ctrl_col1:
    search_q = st.text_input(
        "🔍 Search",
        placeholder="Filter by Order Number or Customer Name…",
        label_visibility="collapsed",
    )
with ctrl_col2:
    if not pivot_df.empty:
        export_bytes = export_to_excel(
            pivot_df.drop(columns=["_total_pending"], errors="ignore"),
            sheet_title="CDPL Orders",
        )
        st.download_button(
            label="📥 Export Excel",
            data=export_bytes,
            file_name=f"Order_Status_{pd.Timestamp.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ── Search filter ─────────────────────────────────────────────────────────
display_df = pivot_df.copy()
if search_q.strip():
    q = search_q.strip().lower()
    mask = (
        display_df["Order Number"].str.lower().str.contains(q, na=False) |
        display_df["Customer Name"].str.lower().str.contains(q, na=False)
    )
    display_df = display_df[mask]

# ── Two-tier table ────────────────────────────────────────────────────────
render_two_tier_table(
    display_df.drop(columns=["_total_pending"], errors="ignore"),
    show_totals=True,
    height=600,
)

if display_df.empty and search_q.strip():
    st.warning(f"No orders match '{search_q}'.")
elif pivot_df.empty:
    st.info("No orders found in the dataset.")
