"""
app.py
CTPL ERP Flat-Glass Processing — Automated Reporting Dashboard
Enterprise Streamlit Application | Single-View Architecture
"""
from __future__ import annotations

import hashlib
import pandas as pd
import streamlit as st

from core.aggregation import build_pivot_df, build_unit_df, tag_order_status
from core.excel_exporter import export_to_excel
from core.ingestion import load_erp_excel
from core.email_sync import email_file
from components.two_tier_table import render_two_tier_table

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CTPL Glass Reporting",
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
        <span style="background: linear-gradient(135deg, #38bdf8, #0284c7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">CTPL</span> Glass Processing
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
    st.markdown("#### 📥 Upload Production Data")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**GS Orders**")
        uploaded_gs = st.file_uploader(
            "Select GS files",
            type=["xlsx"],
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="gs"
        )
    with col2:
        st.markdown("**FRG Orders**")
        uploaded_frg = st.file_uploader(
            "Select FRG files",
            type=["xlsx"],
            label_visibility="collapsed",
            accept_multiple_files=True,
            key="frg"
        )


def _md5(files: list) -> str:
    import hashlib
    h = hashlib.md5()
    for f in files:
        h.update(f.read())
        f.seek(0)
    return h.hexdigest()


def _process_files(files: list) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the full ingestion -> unit -> pivot pipeline."""
    raw_dfs = [load_erp_excel(f) for f in files]
    import pandas as pd
    raw_df = pd.concat(raw_dfs, ignore_index=True) if raw_dfs else pd.DataFrame()
    unit_df   = build_unit_df(raw_df)
    pivot_df  = build_pivot_df(unit_df)
    return raw_df, unit_df, pivot_df


def process_upload(files, hash_key, pivot_key):
    if not files:
        if hash_key in st.session_state:
            st.session_state.pop(hash_key, None)
            st.session_state.pop(pivot_key, None)
        return

    file_hash = _md5(files)
    if st.session_state.get(hash_key) != file_hash:
        with st.spinner(f"⏳ Processing data…"):
            raw_df, unit_df, pivot_df = _process_files(files)
            pivot_df = tag_order_status(pivot_df)
            
            for f in files:
                email_file(f.getvalue(), f.name)
                
            st.session_state[hash_key] = file_hash
            st.session_state[pivot_key] = pivot_df

process_upload(uploaded_gs, "hash_gs", "pivot_gs")
process_upload(uploaded_frg, "hash_frg", "pivot_frg")

pivot_gs = tag_order_status(st.session_state["pivot_gs"].copy()) if "pivot_gs" in st.session_state else pd.DataFrame()
pivot_frg = tag_order_status(st.session_state["pivot_frg"].copy()) if "pivot_frg" in st.session_state else pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard View
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Dashboard View
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["GS Orders Dashboard", "FRG Orders Dashboard"])

def render_tab(pivot_df, prefix):
    # Filter ROWS and COLUMNS based on the tab!
    if not pivot_df.empty:
        if prefix == "GS":
            # GS Tab: Keep non-FR orders, drop FRG columns
            pivot_df = pivot_df[~pivot_df["Order Number"].astype(str).str.upper().str.startswith("FR")]
            gs_drop = ["BOROPANE (Ordered)", "GLAZING TAPE (Ordered)", "PYROBEL-T (Ordered)", "BOROPANE (Pending)", "GLAZING TAPE (Pending)", "PYROBEL-T (Pending)", "FRG (Pending)"]
            pivot_df = pivot_df.drop(columns=gs_drop, errors="ignore")
        elif prefix == "FRG":
            # FRG Tab: Keep FR orders, drop GS columns
            pivot_df = pivot_df[pivot_df["Order Number"].astype(str).str.upper().str.startswith("FR")]
            other_cats = [
                "TEMP (Ordered)", "LAMI (Ordered)", "IGU (Ordered)", "LAMI + IGU (Ordered)", "ANI (Ordered)",
                "TEMP (Pending)", "LAMI (Pending)", "IGU (Pending)", "LAMI + IGU (Pending)", "ANI (Pending)"
            ]
            pivot_df = pivot_df.drop(columns=other_cats, errors="ignore")

    ctrl_col1, ctrl_col2 = st.columns([3, 1])
    with ctrl_col1:
        search_q = st.text_input(
            f"🔍 Search {prefix}",
            placeholder="Filter by Order Number or Customer Name…",
            label_visibility="collapsed",
            key=f"search_{prefix}"
        )
    with ctrl_col2:
        if not pivot_df.empty:
            export_bytes = export_to_excel(
                pivot_df.drop(columns=["_total_pending"], errors="ignore"),
                sheet_title=f"{prefix} Orders",
            )
            st.download_button(
                label=f"📥 Download {prefix} Report",
                data=export_bytes,
                file_name=f"{prefix}_Status_{pd.Timestamp.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"dl_{prefix}"
            )

    display_df = pivot_df.copy()
    if search_q.strip():
        q = search_q.strip().lower()
        mask = (
            display_df["Order Number"].str.lower().str.contains(q, na=False) |
            display_df["Customer Name"].str.lower().str.contains(q, na=False)
        )
        display_df = display_df[mask]

    render_two_tier_table(
        display_df.drop(columns=["_total_pending"], errors="ignore"),
        show_totals=True,
        height=600,
    )

    if display_df.empty and search_q.strip():
        st.warning(f"No orders match '{search_q}'.")
    elif pivot_df.empty:
        st.info("No orders found in the dataset.")

with tab1:
    render_tab(pivot_gs, "GS")

with tab2:
    render_tab(pivot_frg, "FRG")