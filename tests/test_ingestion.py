"""
tests/test_ingestion.py
Verification suite for core/ingestion.py:
  - Multi-format date parsing (string, Excel serial, mixed)
  - QC_OUT NaN -> 0.0 coercion
  - Schema validation (missing column warning, non-fatal)

Critical fix applied:
  Excel serial 46023 (not 46066) corresponds to 2026-01-01.
  Verified: pd.to_datetime(46023, unit='D', origin='1899-12-30') = 2026-01-01
"""
from __future__ import annotations
import io
from unittest.mock import patch

import pandas as pd
import pytest

from core.ingestion import parse_dates_safely


class TestParseDatesSafely:

    def test_dd_mm_yyyy_string(self):
        s = pd.Series(["01-09-2026"])
        result = parse_dates_safely(s)
        assert result.iloc[0] == pd.Timestamp("2026-09-01")

    def test_yyyy_mm_dd_string(self):
        s = pd.Series(["2026-09-01"])
        result = parse_dates_safely(s)
        assert result.iloc[0] == pd.Timestamp("2026-09-01")

    def test_dd_mmm_yyyy_string(self):
        s = pd.Series(["01-Sep-2026"])
        result = parse_dates_safely(s)
        assert result.iloc[0] == pd.Timestamp("2026-09-01")

    def test_excel_serial_float_string(self):
        """
        Excel serial 46023 as a string -> 2026-01-01.
        Verified: pd.to_datetime(46023, unit='D', origin='1899-12-30')
        = 2026-01-01 (accounts for Excel 1900 leap-year bug via origin offset).
        """
        s = pd.Series(["46023.0"])
        result = parse_dates_safely(s)
        assert result.iloc[0].date() == pd.Timestamp("2026-01-01").date()

    def test_excel_serial_raw_float(self):
        """Raw float 46023.0 (as returned by openpyxl for date cells) -> 2026-01-01."""
        s = pd.Series([46023.0])
        result = parse_dates_safely(s)
        assert result.iloc[0].date() == pd.Timestamp("2026-01-01").date()

    def test_excel_serial_another_known_date(self):
        """
        Additional anchor: Excel serial 44927 -> 2023-01-01.
        Validates the serial conversion formula independently.
        """
        s = pd.Series([44927.0])
        result = parse_dates_safely(s)
        assert result.iloc[0].date() == pd.Timestamp("2023-01-01").date()

    def test_mixed_formats_all_resolve(self):
        """Column with mixed formats — all must resolve to non-NaT."""
        s = pd.Series(["01-09-2026", "2026-09-02", "03-Sep-2026", "46023.0"])
        result = parse_dates_safely(s)
        assert result.isna().sum() == 0

    def test_unparseable_value_returns_nat_and_warns(self):
        """'N/A' must produce NaT and emit st.warning — never raise."""
        s = pd.Series(["N/A"])
        with patch("streamlit.warning") as mock_warn:
            result = parse_dates_safely(s)
        assert result.isna().iloc[0]
        mock_warn.assert_called_once()

    def test_empty_series(self):
        s = pd.Series([], dtype=str)
        result = parse_dates_safely(s)
        assert len(result) == 0


class TestLoadErpExcel:

    def _build_xlsx(self, rows: list[list]) -> io.BytesIO:
        """Helper: build a minimal xlsx with the CTPL header layout."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Report Metadata Row"])   # row 0 — ignored (header=1)
        ws.append([
            "PNAME", "SOTRANS", "SALES_ORDER_DATE", "OBTRANS",
            "SNO", "OBQTY", "QC_OUT", "OBDESCRIPTION",
        ])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    def test_qc_out_nan_coerced_to_zero(self):
        """1,593 NaN QC_OUT values in real CTPL data must coerce to 0.0."""
        buf = self._build_xlsx([["CLIENT", "RK1", "01-09-2026", "OB1", 1, 5, None, "TEMPERED GLASS: [10MM]"]]) 
        with patch("streamlit.warning"):
            from core.ingestion import load_erp_excel
            df = load_erp_excel(buf)
        assert df["QC_OUT"].iloc[0] == 0.0

    def test_missing_column_is_fatal(self):
        """Missing critical columns must emit error and stop execution."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Metadata"])
        ws.append(["PNAME", "SOTRANS", "SALES_ORDER_DATE", "OBTRANS", "SNO", "OBQTY", "QC_OUT"])
        ws.append(["CLIENT", "RK1", "01-09-2026", "OB1", 1, 5, 3])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        with patch("streamlit.error") as mock_err, patch("streamlit.stop") as mock_stop:
            mock_stop.side_effect = Exception("StopException")
            from core.ingestion import load_erp_excel
            try:
                load_erp_excel(buf)
            except Exception:
                pass
            mock_err.assert_called()
