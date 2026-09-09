"""Strict compatibility frontend for supported prompt-language extensions.

This module intentionally does not add new geometry generators.  It only marks
an extended prompt as fully consumed when the existing deterministic parser has
already extracted every requested value explicitly.  The downstream semantic,
IR, and fabrication validators remain authoritative.
"""

from __future__ import annotations

import re

from .design_graph import DesignGraph
from .prompt_engine import NUM_WORDS, SIGNED_NUMBER_PATTERN, UNIT_PATTERN
from .prompt_engine import generate_design as _generate_design


def _matches_three_modifier_plate(text: str) -> bool:
    """Accept the three plate modifiers that the parser already implements.

    The base grammar historically allowed at most two of holes, slots, and a
    corner radius even though all three are parsed independently.  This
    extension is deliberately narrow: all three modifiers must appear exactly
    once and feature sizes must carry enough unit information to avoid silent
    dimensional defaults.
    """

    number = SIGNED_NUMBER_PATTERN
    unit = rf"(?:{UNIT_PATTERN})"
    measure = rf"{number}\s*{unit}?"
    explicit_measure = rf"{number}\s*{unit}"
    dimensions = rf"{measure}\s*(?:x|by)\s*{measure}\s*(?:x|by)\s*{measure}"
    count_word = "|".join(word for word, value in NUM_WORDS.items() if value > 0)
    count = rf"(?:\d+|{count_word})"
    one_count = r"(?:1|one|a|an)"
    hole = rf"(?:{count}\s+{explicit_measure}\s+(?:diameter\s+)?holes?|{one_count}\s+{explicit_measure}\s+(?:diameter\s+)?hole)"
    slot_dims = rf"{number}\s*{unit}?\s*(?:x|by)\s*{number}\s*{unit}"
    slot = rf"(?:{count}\s+{slot_dims}\s+slots?|{one_count}\s+{slot_dims}\s+slot)"
    corner = rf"corner\s+radius\s+{explicit_measure}"
    modifier = rf"(?:{hole}|{slot}|{corner})"
    suffix = rf"\s+with\s+{modifier}\s+and\s+{modifier}\s+and\s+{modifier}"
    article = r"(?:a|an)"
    plate_noun = r"(?:plate|panel|bracket|mounting\s+board)"

    if len(re.findall(r"\bholes?\b", text)) != 1:
        return False
    if len(re.findall(r"\bslots?\b", text)) != 1:
        return False
    if len(re.findall(r"\bcorner\s+radius\b", text)) != 1:
        return False

    patterns = [
        rf"{article}\s+(?:solid\s+)?{dimensions}\s+(?:rounded\s+)?{plate_noun}{suffix}",
        rf"{article}\s+(?:rounded\s+)?{plate_noun}\s+{measure}\s+wide\s+{measure}\s+deep\s+(?:and\s+)?{measure}\s+thick{suffix}",
    ]
    return any(re.fullmatch(pattern, text) is not None for pattern in patterns)


def _plate_parse_is_explicit(design: DesignGraph) -> bool:
    metadata = design.metadata
    return bool(
        metadata.get("fabrication_domain") == "plate"
        and metadata.get("recognized") is True
        and metadata.get("explicit_dimensions") is True
        and metadata.get("hole_count_explicit") is True
        and metadata.get("hole_diameter_explicit") is True
        and metadata.get("slot_count_explicit") is True
        and metadata.get("slot_dimensions_explicit") is True
        and metadata.get("rounded_requested") is True
        and metadata.get("corner_radius_explicit") is True
    )


def _matches_wall_thickness_after_label(text: str) -> bool:
    """Accept ``with wall thickness 2 mm`` for hollow rectangular enclosures."""

    number = SIGNED_NUMBER_PATTERN
    unit = rf"(?:{UNIT_PATTERN})"
    measure = rf"{number}\s*{unit}?"
    explicit_measure = rf"{number}\s*{unit}"
    dimensions = rf"{measure}\s*(?:x|by)\s*{measure}\s*(?:x|by)\s*{measure}"
    article = r"(?:a|an)"
    hollow_noun = r"(?:case|enclosure|housing|shell)"
    pattern = rf"{article}\s+{dimensions}\s+{hollow_noun}\s+with\s+wall\s+thickness\s+{explicit_measure}"
    return re.fullmatch(pattern, text) is not None


def _wall_parse_is_explicit(design: DesignGraph) -> bool:
    metadata = design.metadata
    return bool(
        metadata.get("fabrication_domain") == "enclosure"
        and metadata.get("recognized") is True
        and metadata.get("explicit_dimensions") is True
        and metadata.get("wall_thickness_explicit") is True
        and metadata.get("wall_thickness_mm") is not None
    )


def generate_design(prompt: str) -> DesignGraph:
    """Generate a design while safely extending the documented prompt surface.

    The base parser still performs all numerical extraction and geometry
    generation.  An extension can only change ``prompt_fully_consumed`` after
    a strict whole-string match and after checking that every requested field
    was explicitly extracted.  Semantic validation is never bypassed.
    """

    design = _generate_design(prompt)
    metadata = design.metadata
    if metadata.get("prompt_fully_consumed") is True:
        return design

    text = str(metadata.get("normalized_prompt", ""))
    extension: str | None = None
    if _matches_three_modifier_plate(text) and _plate_parse_is_explicit(design):
        extension = "plate-three-modifier-v1"
    elif _matches_wall_thickness_after_label(text) and _wall_parse_is_explicit(design):
        extension = "enclosure-wall-label-v1"

    if extension is not None:
        metadata["prompt_fully_consumed"] = True
        metadata["prompt_contract_extension"] = extension

    return design
