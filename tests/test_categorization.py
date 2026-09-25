"""
tests/test_categorization.py
Full coverage of classify_glass() across all known CTPL OBDESCRIPTION patterns.
"""
from core.categorization import classify_glass


class TestClassifyGlass:

    # ── TEMP ──────────────────────────────────────────────────────────────────
    def test_tempered_glass(self):
        assert classify_glass("TEMPERED GLASS: [ 10MM CLEAR EDGE POLISH FLAT TEMPERED]") == "TEMP"

    def test_heat_strengthened(self):
        assert classify_glass("HEAT STRENGTHENED GLASS: [ 6MM SOLAR CONTROL NATURA PLUS (CLEAR EDGE ) ROUGH GRINDING]") == "TEMP"

    def test_decor_tempered(self):
        assert classify_glass("DECOR TEMPERED GLASS: [ 6MM CLEAR ROUGH GRINDING ACID FROSTING FLAT TEMPERED PROTECTIVE FILM]") == "TEMP"

    def test_decor_heat_strengthened(self):
        assert classify_glass("DECOR HEAT STRENGTHENED GLASS: [ 8MM CLEAR EDGE POLISH PLAIN FROSTING]") == "TEMP"

    # ── LAMI ──────────────────────────────────────────────────────────────────
    def test_pvb_lami(self):
        assert classify_glass("13.52 MM LAMINATED GLASS: [(LAYER 1: HEAT STRENGTHENED GLASS 6MM CLEAR ROUGH GRINDING) + ( 1.52MM CLEAR PVB) + (LAYER 2: HEAT STRENGTHENED GLASS 6MM CLEAR ROUGH GRINDING) ]") == "LAMI"

    def test_sentryglas_lami(self):
        assert classify_glass("11.52 MM LAMINATED GLASS: [(LAYER 1: TEMPERED GLASS 5MM CLEAR EDGE POLISH FLAT TEMPERED) + ( 2 X 0.76MM SENTRYGLAS) + (LAYER 2: TEMPERED GLASS 5MM CLEAR EDGE POLISH FLAT TEMPERED) ]") == "LAMI"

    def test_evg_lami(self):
        assert classify_glass("10.76 MM LAMINATED GLASS: [5MM + EVA + 5MM]") == "LAMI"

    # ── IGU ───────────────────────────────────────────────────────────────────
    def test_air_gap_igu(self):
        assert classify_glass("22 MM INSULATED GLASS: [(LAYER 1: TEMPERED GLASS 6MM CLEAR ROUGH GRINDING FLAT TEMPERED) + ( 10 AIR GAP) + (LAYER 2: TEMPERED GLASS 6MM CLEAR ROUGH GRINDING FLAT TEMPERED) ]") == "IGU"

    def test_argon_igu(self):
        assert classify_glass("24 MM INSULATED GLASS: [(LAYER 1: TEMPERED GLASS 6MM SOLAR CONTROL NATURA PRO ROUGH GRINDING FLAT TEMPERED) + ( 12 AIR GAP ARGON GAS GAP) + (LAYER 2: TEMPERED GLASS 6MM CLEAR ROUGH GRINDING FLAT TEMPERED) ]") == "IGU"

    def test_venetian_blinds_igu(self):
        """Integral blind IGU — confirmed in real CTPL data."""
        assert classify_glass("34 MM INSULATED GLASS: [(LAYER 1: TEMPERED GLASS 6MM CLEAR ROUGH GRINDING FLAT TEMPERED) + ( MANUAL BLINDS 22 AIR GAP VENETIAN BLINDS) + (LAYER 2: TEMPERED GLASS 6MM CLEAR ROUGH GRINDING FLAT TEMPERED) ]") == "IGU"

    # ── LAMI + IGU ────────────────────────────────────────────────────────────
    def test_lami_igu_pvb_air_gap(self):
        assert classify_glass("24.52 MM INSULATED GLASS: [(LAYER 1: 9.52 MM LAMINATED GLASS {(LAYER 1-1: TEMPERED GLASS 4MM CLEAR ROUGH GRINDING FLAT TEMPERED) + ( 1.52MM CLEAR PVB) + (LAYER 1-2: TEMPERED GLASS 4MM CLEAR ROUGH GRINDING FLAT TEMPERED)  }) + ( 10 AIR GAP) + (LAYER 2: TEMPERED GLASS 5MM CLEAR ROUGH GRINDING FLAT TEMPERED) ]") == "LAMI + IGU"

    def test_lami_igu_sentryglas_argon(self):
        assert classify_glass("29.52 MM INSULATED GLASS: [(LAYER 1: TEMPERED GLASS 6MM SOLAR CONTROL SPRING PLUS (CLEAR ENHANCE) ROUGH GRINDING FLAT TEMPERED) + ( 12 AIR GAP ARGON GAS GAP) + (LAYER 2: 11.52 MM LAMINATED GLASS {(LAYER 2-1: HEAT STRENGTHENED GLASS 5MM CLEAR ROUGH GRINDING) + ( 1.52MM CLEAR PVB) + (LAYER 2-2: HEAT STRENGTHENED GLASS 5MM CLEAR ROUGH GRINDING)  }) ]") == "LAMI + IGU"

    # ── Edge cases ────────────────────────────────────────────────────────────
    def test_none_returns_temp(self):
        assert classify_glass(None) == "TEMP"  # type: ignore

    def test_empty_string_returns_temp(self):
        assert classify_glass("") == "TEMP"

    def test_whitespace_returns_temp(self):
        assert classify_glass("   ") == "TEMP"
