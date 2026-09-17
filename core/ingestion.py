"""
core/ingestion.py
Resilient CDPL ERP Excel loader with multi-format date parsing
and Excel serial float fallback.
"""
from __future__ import annotations

import logging
import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

REQUIRED_COLS = [
    "PNAME", "SOTRANS", "SALES_ORDER_DATE",
    "OBTRANS", "SNO", "OBQTY", "QC_OUT", "OBDESCRIPTION",
    "T", "LAY", "II",
]


def parse_dates_safely(series: pd.Series) -> pd.Series:
    """
    Multi-format date parser with Excel serial float fallback.
    """
    series_str = series.astype(str).str.strip()
    is_numeric = series_str.str.match(r'^\d+(\.\d+)?$')

    parsed = pd.Series(pd.NaT, index=series.index)

    # Process string dates
    str_idx = series.index[~is_numeric]
    if len(str_idx):
        s = series_str.loc[str_idx]
        p = pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")
        p = p.fillna(pd.to_datetime(s, format="%Y-%m-%d", errors="coerce"))
        p = p.fillna(pd.to_datetime(s, format="%d-%b-%Y", errors="coerce"))
        p = p.fillna(pd.to_datetime(s, errors="coerce", dayfirst=True))
        parsed.loc[str_idx] = p

    # Process numeric serials
    num_idx = series.index[is_numeric]
    if len(num_idx):
        serial_dates = pd.to_datetime(
            pd.to_numeric(series.loc[num_idx], errors="coerce"),
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        ).dt.floor("D")
        parsed.loc[num_idx] = serial_dates.values

    # Pass 3 — report remaining NaT
    still_nat = parsed.isna()
    if still_nat.any():
        bad_vals = series.loc[still_nat[still_nat].index].unique()[:5].tolist()
        msg = (
            f"\u26a0\ufe0f **{still_nat.sum()} date(s) could not be parsed** "
            f"and will be excluded.  Sample values: `{bad_vals}`"
        )
        st.warning(msg)
        logger.warning("Unparseable SALES_ORDER_DATE values: %s", bad_vals)

    return parsed


def load_erp_excel(file) -> pd.DataFrame:
    """
    Load and validate a raw CDPL ERP Excel export.

    Contract:
    - Header at row index 1 (Excel row 2, confirmed from real CDPL data).
    - All columns read as str to prevent openpyxl type surprises.
    - Returns a clean DataFrame ready for aggregation.
    - Never raises on bad data — emits st.warning() instead.
    """
    df = pd.read_excel(file, header=1, dtype=str)

    # Normalise column names (strip whitespace)
    df.columns = df.columns.str.strip()

    # Schema validation (non-fatal)
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        st.warning(
            f"\u26a0\ufe0f Missing expected columns: `{missing_cols}`. "
            "Processing will continue with available columns."
        )

    # Drop fully-blank rows
    df = df.dropna(how="all").reset_index(drop=True)

    # Resilient date parsing
    if "SALES_ORDER_DATE" in df.columns:
        df["SALES_ORDER_DATE"] = parse_dates_safely(df["SALES_ORDER_DATE"])
        df = df.dropna(subset=["SALES_ORDER_DATE"]).reset_index(drop=True)

    # Numeric coercion
    if "OBQTY" in df.columns:
        df["OBQTY"] = (
            pd.to_numeric(df["OBQTY"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
    
    for col in ["QC_OUT", "T", "LAY", "II"]:
        if col in df.columns:
            df[col] = (
                pd.to_numeric(df[col], errors="coerce")
                .fillna(0.0)
                .astype(float)
            )

    return df
