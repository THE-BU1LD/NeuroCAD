"""Bounded decimal quantities for explicit conversational edits, without guessing units."""
from __future__ import annotations

import math
import re
from decimal import Decimal, localcontext

_SMALL = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
          "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_VALUES = {word: value for value, word in enumerate(_SMALL)}
_VALUES.update({word: value * 10 for value, word in enumerate(_TENS, 2)})
_DIGIT = "(?:" + "|".join(_SMALL[:10]) + ")"
_INTEGER = "(?:" + "|".join(_TENS) + ")(?:[ -](?:" + "|".join(_SMALL[1:10]) + "))?"
_INTEGER = "(?:" + _INTEGER + "|" + "|".join(_SMALL) + ")"
QUANTITY = rf"(?:\d+(?:\.\d+)?|{_INTEGER}(?:\s+point\s+{_DIGIT}(?:\s+{_DIGIT})*)?)"
_QUANTITY_PATTERN = re.compile(QUANTITY)
UNITS = {"mm": 1.0, "millimeter": 1.0, "millimeters": 1.0, "millimetre": 1.0,
         "millimetres": 1.0, "cm": 10.0, "centimeter": 10.0, "centimeters": 10.0,
         "centimetre": 10.0, "centimetres": 10.0, "in": 25.4, "inch": 25.4, "inches": 25.4}
_DECIMAL_UNITS = {unit: Decimal(str(scale)) for unit, scale in UNITS.items()}
UNIT = "|".join(sorted(UNITS, key=len, reverse=True))
MEASURE = rf"(?P<value>{QUANTITY})\s*(?P<unit>{UNIT})"


def millimeters(value: str, unit: str) -> Decimal:
    """Parse the whole quantity, retaining decimal arithmetic until canonicalization."""
    if len(value) > 128 or not _QUANTITY_PATTERN.fullmatch(value) or unit not in _DECIMAL_UNITS:
        raise ValueError("Quantity must be a bounded decimal or zero through ninety-nine, with an explicit supported unit")
    if value[0].isdecimal():
        number = Decimal(value)
    else:
        # Grammar accepts whitespace around 'point'; split tokens to normalize it.
        tokens = value.replace("-", " ").split()
        if "point" in tokens:
            index = tokens.index("point")
            integer_tokens, fraction_tokens = tokens[:index], tokens[index + 1:]
        else:
            integer_tokens, fraction_tokens = tokens, []
        whole = sum(_VALUES[token] for token in integer_tokens)
        digits = "".join(str(_VALUES[token]) for token in fraction_tokens)
        number = Decimal(str(whole) + ("." + digits if digits else ""))
    with localcontext() as context:
        context.prec = 160
        return number * _DECIMAL_UNITS[unit]


def canonical_number(value: Decimal) -> str:
    """Emit fixed decimal notation accepted by the existing canonical edit grammar."""
    converted = float(value)
    if not value.is_finite() or not math.isfinite(converted) or value < 0 or (value and converted == 0):
        raise ValueError("Quantity must be nonnegative and representable in millimeters")
    text = format(value, "f")
    if len(text) > 160:
        raise ValueError("Quantity exceeds the canonical edit precision bound")
    return text


def adjusted_value(baseline: float, delta: Decimal, *, subtract: bool) -> Decimal:
    """Resolve a delta once against the original project, never a preceding edit."""
    with localcontext() as context:
        context.prec = 160
        current = Decimal(str(baseline))
        return current - delta if subtract else current + delta


def diameter_from_radius(radius: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 160
        return radius * 2
