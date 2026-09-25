"""
tests/test_aggregation.py
Mathematical correctness: deduplication, bottleneck MIN, overproduction clamp,
status tagging.
"""
from __future__ import annotations
import pandas as pd
import pytest
from core.aggregation import build_unit_df, build_pivot_df, tag_order_status


def _raw(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["SALES_ORDER_DATE"] = pd.to_datetime(df["SALES_ORDER_DATE"])
    df["OBQTY"]  = df["OBQTY"].astype(int)
    df["QC_OUT"] = df["QC_OUT"].astype(float)
    return df


class TestBuildUnitDf:

    def test_single_layer_temp(self):
        raw = _raw([{
            "SOTRANS": "RK1", "OBTRANS": "OB1", "SNO": 1,
            "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
            "OBDESCRIPTION": "TEMPERED GLASS: [10MM CLEAR]",
            "OBQTY": 5, "QC_OUT": 5.0,
        }])
        unit = build_unit_df(raw)
        assert len(unit) == 1
        assert unit.iloc[0]["Ordered_Qty"] == 5
        assert unit.iloc[0]["FG_Qty"]      == 5
        assert unit.iloc[0]["Pending_Qty"] == 0
        assert unit.iloc[0]["Category"]    == "TEMP"

    def test_two_layer_dgu_bottleneck(self):
        """Layer 2 QC_OUT=10 must cap FG at 10 for the whole IGU unit."""
        desc = "22 MM INSULATED GLASS: [(LAYER 1: ...) + ( 10 AIR GAP) + (LAYER 2: ...)]"
        raw = _raw([
            {"SOTRANS": "RK1", "OBTRANS": "OB1", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 50, "QC_OUT": 50.0},
            {"SOTRANS": "RK1", "OBTRANS": "OB1", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 50, "QC_OUT": 10.0},
        ])
        unit = build_unit_df(raw)
        assert len(unit) == 1
        assert unit.iloc[0]["Ordered_Qty"] == 50
        assert unit.iloc[0]["FG_Qty"]      == 10
        assert unit.iloc[0]["Pending_Qty"] == 40
        assert unit.iloc[0]["Category"]    == "IGU"

    def test_three_layer_lami_igu(self):
        """3-layer composite with one NaN-coerced layer at 0 -> FG=0."""
        desc = "24.52 MM INSULATED GLASS: [(LAYER 1: 9.52 MM LAMINATED GLASS {... 1.52MM CLEAR PVB ...}) + ( 10 AIR GAP) + (LAYER 2: ...)]"
        raw = _raw([
            {"SOTRANS": "RK2", "OBTRANS": "OB2", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 2, "QC_OUT": 2.0},
            {"SOTRANS": "RK2", "OBTRANS": "OB2", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 2, "QC_OUT": 2.0},
            {"SOTRANS": "RK2", "OBTRANS": "OB2", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 2, "QC_OUT": 0.0},  # was NaN in ERP
        ])
        unit = build_unit_df(raw)
        assert unit.iloc[0]["FG_Qty"]      == 0
        assert unit.iloc[0]["Pending_Qty"] == 2
        assert unit.iloc[0]["Category"]    == "LAMI + IGU"

    def test_overproduction_clamp(self):
        """QC_OUT > OBQTY must never produce negative Pending_Qty."""
        raw = _raw([{
            "SOTRANS": "RK3", "OBTRANS": "OB3", "SNO": 1,
            "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
            "OBDESCRIPTION": "TEMPERED GLASS: [10MM]",
            "OBQTY": 50, "QC_OUT": 52.0,
        }])
        unit = build_unit_df(raw)
        assert unit.iloc[0]["Pending_Qty"] == 0

    def test_no_overcounting(self):
        """Deduplicated ordered qty must be less than raw OBQTY sum for 2-layer unit."""
        desc = "22 MM INSULATED GLASS: [(LAYER 1: ...) + ( 10 AIR GAP) + (LAYER 2: ...)]"
        raw = _raw([
            {"SOTRANS": "RK4", "OBTRANS": "OB4", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 50, "QC_OUT": 0.0},
            {"SOTRANS": "RK4", "OBTRANS": "OB4", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 50, "QC_OUT": 0.0},
        ])
        unit = build_unit_df(raw)
        assert raw["OBQTY"].sum() == 100       # raw inflated
        assert unit["Ordered_Qty"].sum() == 50  # correctly deduplicated


    def test_dynamic_fg_calculation(self):
        """FG should be strictly QC_OUT"""
        desc = "TEMPERED GLASS: [10MM CLEAR]"
        raw = _raw([
            {"SOTRANS": "RK_T", "OBTRANS": "OB1", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": desc, "OBQTY": 50, "QC_OUT": 0.0, "T": 50.0},
             {"SOTRANS": "RK_LAMI", "OBTRANS": "OB2", "SNO": 1,
             "PNAME": "C", "SALES_ORDER_DATE": "2026-09-01",
             "OBDESCRIPTION": "LAMINATED GLASS: [5MM]", "OBQTY": 10, "QC_OUT": 5.0, "LAY": 10.0},
        ])
        unit = build_unit_df(raw)
        
        t_unit = unit[unit["SOTRANS"] == "RK_T"].iloc[0]
        assert t_unit["FG_Qty"] == 0
        
        lami_unit = unit[unit["SOTRANS"] == "RK_LAMI"].iloc[0]
        assert lami_unit["FG_Qty"] == 5

class TestTagOrderStatus:

    def _pivot(self, sotrans, pending):
        return pd.DataFrame([{
            "Order Number": sotrans,
            "TEMP (Pending)": pending, "LAMI (Pending)": 0,
            "IGU (Pending)": 0, "LAMI + IGU (Pending)": 0,
        }])

    def test_active(self):
        r = tag_order_status(self._pivot("RK1", 5))
        assert r.iloc[0]["_total_pending"] == 5

    def test_completed(self):
        r = tag_order_status(self._pivot("RK2", 0))
        assert r.iloc[0]["_total_pending"] == 0
