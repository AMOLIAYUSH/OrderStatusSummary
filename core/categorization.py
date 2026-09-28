"""
core/categorization.py
Keyword-based glass make-up classifier.
Classification is performed on the full composite OBDESCRIPTION string,
which is confirmed identical across all constituent layers of a unit.
"""
from __future__ import annotations
import re

# Full regional flat-glass keyword sets (case-insensitive)
IGU_PATTERN = re.compile(
    r"INSULATED|AIR\s*GAP|ARGON|IGU|DGU|DOUBLE\s*GLAZ|TRIPLE\s*GLAZ|"
    r"SPACER|12A|16A|VENETIAN\s*BLINDS|BLINDS\s+\d+\s*AIR",
    re.IGNORECASE,
)

LAMI_PATTERN = re.compile(
    r"LAMINATED|PVB|SENTRYGLAS|EVA|SGP|LAMI(?!NATED)|SENT",
    re.IGNORECASE,
)


def classify_glass(description: str) -> str:
    """
    Classify a finished glass unit by its composite OBDESCRIPTION.
    Priority logic:
      FRG (Boropane, Borosilicate, Glazing Tape, PYROBEL-T)
      LAMI + IGU
      IGU
      LAMI
      ANI (Annealed)
      TEMP (Fallback)
    """
    if not isinstance(description, str) or not description.strip():
        return "TEMP"

    desc = description.upper()

    if "BOROPANE" in desc or "BOROSILICATE" in desc or "GLAZING TAPE" in desc or "PYROBEL-T" in desc:
        return "FRG"

    has_igu  = bool(IGU_PATTERN.search(description))
    has_lami = bool(LAMI_PATTERN.search(description))

    if has_igu and has_lami:
        return "LAMI + IGU"
    elif has_igu:
        return "IGU"
    elif has_lami:
        return "LAMI"
    elif "ANNEALED" in desc:
        return "ANI"
    else:
        return "TEMP"
