"""
components/two_tier_table.py
Sandboxed HTML two-tier table renderer using st.components.v1.html().
Prevents Streamlit markdown indentation bugs by rendering in an iframe.
"""
from __future__ import annotations

import pandas as pd
import streamlit.components.v1 as components

COL_GROUPS = [
    {
        "label": "MASTER DATA",
        "cols":  ["Order Number", "Customer Name", "Order Date"],
        "color": "#86EFAC",
    },
    {
        "label": "ORDERED QUANTITY",
        "cols":  [
            "TEMP (Ordered)", "LAMI (Ordered)", "IGU (Ordered)",
            "LAMI + IGU (Ordered)", "Total Quantity Ordered",
        ],
        "color": "#67E8F9",
    },
    {
        "label": "FINISHED GOODS",
        "cols":  ["Finished Goods Quantity"],
        "color": "#A7F3D0",
    },
    {
        "label": "EXCEPTIONS",
        "cols":  ["Rejected Quantity", "Cancelled Quantity"],
        "color": "#FDA4AF",
    },
    {
        "label": "PENDING QUANTITY",
        "cols":  [
            "TEMP (Pending)", "LAMI (Pending)",
            "IGU (Pending)", "LAMI + IGU (Pending)",
        ],
        "color": "#67E8F9",
    },
    {
        "label": "ORDER STATUS",
        "cols":  ["Status", "Plan Order Status"],
        "color": "#D1D5DB",
    }
]

NUMERIC_COLS_SET = {
    "TEMP (Ordered)", "LAMI (Ordered)", "IGU (Ordered)", "LAMI + IGU (Ordered)",
    "Total Quantity Ordered", "Finished Goods Quantity", "Rejected Quantity", "Cancelled Quantity",
    "TEMP (Pending)", "LAMI (Pending)", "IGU (Pending)", "LAMI + IGU (Pending)",
}

_CSS = """
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Calibri, sans-serif; font-size: 12px; background: #fff; }
.wrap { overflow-x: auto; max-height: 520px; overflow-y: auto; }
table {
    border-collapse: collapse; width: 100%; min-width: 960px;
    border: 1px solid #CBD5E1;
}
th, td { border: 1px solid #CBD5E1; padding: 5px 9px; white-space: nowrap; }
.t1 { font-weight: 700; text-align: center; font-size: 11px; color: #1E293B; }
.t2 { background: #F472B6 !important; font-weight: 700; text-align: center;
      font-size: 10px; color: #1E293B; }
.total-row td { background: #FEF9C3 !important; font-weight: 700; }
tbody tr:nth-child(odd)  td { background: #FFFFFF; }
tbody tr:nth-child(even) td { background: #F8FAFC; }
tbody tr:hover td { background: #EFF6FF !important; }
.num    { text-align: right; }
.left   { text-align: left; }
.center { text-align: center; }
code {
    background: #F1F5F9; padding: 1px 4px; border-radius: 3px;
    font-family: monospace; font-size: 11px;
}
</style>
"""


def _fmt_num(val) -> str:
    try:
        return f"{int(val):,}"
    except (TypeError, ValueError):
        return "0"


def build_two_tier_html(df: pd.DataFrame, show_totals: bool = True) -> str:
    """Generate sandboxed HTML string for the two-tier pivot table."""
    active_groups = []
    for group in COL_GROUPS:
        present = [c for c in group["cols"] if c in df.columns]
        if present:
            active_groups.append({**group, "cols": present})

    all_cols = [c for g in active_groups for c in g["cols"]]
    parts = [_CSS, '<div class="wrap"><table><thead>']

    # Tier 1 headers
    parts.append("<tr>")
    for g in active_groups:
        n = len(g["cols"])
        parts.append(
            f'<th class="t1" colspan="{n}" '
            f'style="background:{g["color"]}">{g["label"]}</th>'
        )
    parts.append("</tr>")

    # Tier 2 subheaders
    parts.append("<tr>")
    for col in all_cols:
        parts.append(f'<th class="t2">{col}</th>')
    parts.append("</tr></thead><tbody>")

    # Data rows
    for _, row in df.iterrows():
        parts.append("<tr>")
        for col in all_cols:
            val = row.get(col, "")
            if col in NUMERIC_COLS_SET:
                parts.append(f'<td class="num">{_fmt_num(val)}</td>')
            elif col == "Order Number":
                parts.append(f'<td class="left"><code>{val}</code></td>')
            elif col == "Order Date":
                parts.append(f'<td class="center">{val}</td>')
            elif col == "Plan Order Status":
                safe = str(val).replace("<", "&lt;").replace(">", "&gt;") if pd.notna(val) else ""
                if safe == "Ready":
                    parts.append(f'<td class="center" style="background:#86EFAC !important; font-weight:700;">{safe}</td>')
                elif "pending" in safe:
                    parts.append(f'<td class="left" style="background:#FEF08A !important; font-weight:700;">{safe}</td>')
                else:
                    parts.append(f'<td class="left">{safe}</td>')
            else:
                safe = (
                    str(val).replace("<", "&lt;").replace(">", "&gt;")
                    if pd.notna(val) else ""
                )
                parts.append(f'<td class="left">{safe}</td>')
        parts.append("</tr>")

    # TOTAL row
    if show_totals and not df.empty:
        parts.append('<tr class="total-row">')
        for col in all_cols:
            if col == "Order Number":
                parts.append('<td class="center"><strong>TOTAL</strong></td>')
            elif col in NUMERIC_COLS_SET:
                total = df[col].sum() if col in df.columns else 0
                parts.append(f'<td class="num"><strong>{_fmt_num(total)}</strong></td>')
            else:
                parts.append("<td></td>")
        parts.append("</tr>")

    parts.append("</tbody></table></div>")
    return "".join(parts)


def render_two_tier_table(
    df: pd.DataFrame,
    show_totals: bool = True,
    height: int = 580,
) -> None:
    """Render the two-tier table in a sandboxed HTML iframe via Streamlit."""
    if df.empty:
        import streamlit as st
        st.info("No data to display.")
        return
    html = build_two_tier_html(df, show_totals=show_totals)
    components.html(html, height=height, scrolling=True)
