"""
core/aggregation.py
Unit deduplication, bottleneck QC solver, and 13-column master pivot engine.
"""
from __future__ import annotations
import pandas as pd
from core.categorization import classify_glass

GROUP_KEYS  = ["SOTRANS", "OBTRANS", "SNO"]
PIVOT_KEYS  = ["SOTRANS", "PNAME", "SALES_ORDER_DATE"]
CATEGORIES  = ["TEMP", "LAMI", "IGU", "LAMI + IGU"]

OUTPUT_COLS = [
    "Order Number", "Customer Name", "Order Date",
    "TEMP (Ordered)", "LAMI (Ordered)", "IGU (Ordered)", "LAMI + IGU (Ordered)",
    "Total Quantity Ordered", "Finished Goods Quantity", "Rejected Quantity", "Cancelled Quantity",
    "TEMP (Pending)", "LAMI (Pending)", "IGU (Pending)", "LAMI + IGU (Pending)",
    "Plan Order Status"
]

PENDING_COLS = [
    "TEMP (Pending)", "LAMI (Pending)",
    "IGU (Pending)", "LAMI + IGU (Pending)",
]


def build_unit_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse raw ERP layer rows -> one row per finished glass unit.

    Deduplication key: (SOTRANS, OBTRANS, SNO)
    Ordered_Qty = MAX(OBQTY)   - defensive; confirmed identical in real data
    FG_Qty      = MIN(QC_OUT)  - bottleneck: unit only as complete as slowest layer
    Pending_Qty = clip(Ordered - FG, lower=0)  - overproduction guard
    Category    = classify_glass(OBDESCRIPTION.first())
    """
    if df.empty:
        return pd.DataFrame(columns=GROUP_KEYS + [
            "PNAME", "SALES_ORDER_DATE", "OBDESCRIPTION",
            "Ordered_Qty", "FG_Qty", "Pending_Qty", "Category",
        ])

    for col in ["T", "LAY", "II"]:
        if col not in df.columns:
            df[col] = 0.0
    for col in ["REJ_QTY", "SFO_SHOT_QTY"]:
        if col not in df.columns:
            df[col] = 0.0

    unit_df = (
        df.groupby(GROUP_KEYS, sort=False)
        .agg(
            PNAME            =("PNAME",             "first"),
            SALES_ORDER_DATE =("SALES_ORDER_DATE",  "first"),
            OBDESCRIPTION    =("OBDESCRIPTION",     "first"),  # identical across layers
            Ordered_Qty      =("OBQTY",             "max"),    # defensive MAX
            QC_OUT           =("QC_OUT",            "min"),
            T                =("T",                 "min"),
            LAY              =("LAY",               "min"),
            II               =("II",                "min"),
            Rejected_Qty     =("REJ_QTY",           "max"),
            Cancelled_Qty    =("SFO_SHOT_QTY",      "max"),
        )
        .reset_index()
    )

    unit_df["Category"] = unit_df["OBDESCRIPTION"].apply(classify_glass)

    def _calc_fg(row):
        cat = row["Category"]
        qc = row["QC_OUT"]
        if cat == "TEMP": return max(qc, row["T"])
        if cat == "LAMI": return max(qc, row["LAY"])
        if cat in ["IGU", "LAMI + IGU"]: return max(qc, row["II"])
        return qc

    unit_df["FG_Qty"] = unit_df.apply(_calc_fg, axis=1)

    unit_df["Pending_Qty"] = (
        unit_df["Ordered_Qty"] - unit_df["FG_Qty"] - unit_df["Cancelled_Qty"]
    ).clip(lower=0).astype(int)

    unit_df["FG_Qty"]        = unit_df["FG_Qty"].astype(int)
    unit_df["Rejected_Qty"]  = unit_df["Rejected_Qty"].astype(int)
    unit_df["Cancelled_Qty"] = unit_df["Cancelled_Qty"].astype(int)

    return unit_df


def build_pivot_df(unit_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate unit_df -> one row per Sales Order (13 standardised columns).
    """
    if unit_df.empty:
        return pd.DataFrame(columns=OUTPUT_COLS)

    # Sort by date descending so the output is latest to oldest
    if "SALES_ORDER_DATE" in unit_df.columns:
        unit_df = unit_df.sort_values(by="SALES_ORDER_DATE", ascending=False)

    rows = []
    for keys, grp in unit_df.groupby(PIVOT_KEYS, sort=False):
        sotrans, pname, order_date = keys

        date_str = (
            order_date.strftime("%d-%b-%Y")
            if hasattr(order_date, "strftime") else str(order_date)
        )

        r = {
            "Order Number":  sotrans,
            "Customer Name": pname,
            "Order Date":    date_str,
        }

        ok_parts = []
        pending_parts = []
        abbr = {"TEMP": "Tem", "LAMI": "LAMI", "IGU": "IGU", "LAMI + IGU": "LAMI+IGU"}

        for cat in CATEGORIES:
            sub = grp[grp["Category"] == cat]
            ord_qty = int(sub["Ordered_Qty"].sum())
            pen_qty = int(sub["Pending_Qty"].sum())
            fg_qty  = int(sub["FG_Qty"].sum())
            
            r[f"{cat} (Ordered)"] = ord_qty
            r[f"{cat} (Pending)"] = pen_qty
            
            if fg_qty > 0:
                ok_parts.append(f"{fg_qty} {abbr[cat]}")
            if pen_qty > 0:
                pending_parts.append(f"{pen_qty} {abbr[cat]}")

        if ok_parts and pending_parts:
            r["Plan Order Status"] = f"{', '.join(ok_parts)} OK | {', '.join(pending_parts)} pending"
        elif ok_parts:
            r["Plan Order Status"] = f"{', '.join(ok_parts)} OK"
        elif pending_parts:
            r["Plan Order Status"] = f"{', '.join(pending_parts)} pending"
        else:
            r["Plan Order Status"] = "0 pending"

        r["Total Quantity Ordered"]  = sum(r[f"{c} (Ordered)"] for c in CATEGORIES)
        r["Finished Goods Quantity"] = int(grp["FG_Qty"].sum())
        r["Rejected Quantity"]       = int(grp["Rejected_Qty"].sum())
        r["Cancelled Quantity"]      = int(grp["Cancelled_Qty"].sum())
        rows.append(r)

    return pd.DataFrame(rows, columns=OUTPUT_COLS)


def tag_order_status(pivot_df: pd.DataFrame) -> pd.DataFrame:
    """
    Tag each pivot row with operational status:
      Pending   -> _total_pending > 0
      Completed -> _total_pending == 0
    """
    if pivot_df.empty:
        return pivot_df

    df = pivot_df.copy()
    
    # Pre-compute total pending if not already there
    if "_total_pending" not in df.columns:
        df["_total_pending"] = df[PENDING_COLS].sum(axis=1)

    def _determine_status(row):
        return "Completed" if row["_total_pending"] == 0 else "Pending"

    df["Status"] = df.apply(_determine_status, axis=1)

    return df
