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
      Both IGU + LAMI flags  ->  'LAMI + IGU'
      IGU flag only          ->  'IGU'
      LAMI flag only         ->  'LAMI'
      Neither                ->  'TEMP'

    Safe default: returns 'TEMP' for None / empty strings.
    """
    if not isinstance(description, str) or not description.strip():
        return "TEMP"

    has_igu  = bool(IGU_PATTERN.search(description))
    has_lami = bool(LAMI_PATTERN.search(description))

    if has_igu and has_lami:
        return "LAMI + IGU"
    elif has_igu:
        return "IGU"
    elif has_lami:
        return "LAMI"
    else:
        return "TEMP"
