import re
import math
from typing import List, Dict, Any, Optional, Tuple

# =========================
# CORE CONFIG
# =========================

UNIT_SCALE = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
    "ft": 0.3048,
    "feet": 0.3048,
}

STOPWORDS = set([
    "a","an","the","me","make","create","build","model","of","with","which","is","in","on","at","to","for"
])

# =========================
# REGEX SYSTEM
# =========================

DIM_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches|ft|feet)\s*by\s*"
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches|ft|feet)\s*by\s*"
    r"(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches|ft|feet)",
    re.IGNORECASE,
)

HOLE_RE = re.compile(
    r"hole\s*(?:of|with|radius|diameter)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|m|in|inch|inches)",
    re.IGNORECASE,
)

# =========================
# UTILITIES
# =========================

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"feet|foot", "ft", text)
    text = re.sub(r"inches|inch", "in", text)
    return text


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9\.]+", text)

# =========================
# PARSERS
# =========================

def parse_dimensions(text: str) -> Optional[Tuple[float, float, float]]:
    m = DIM_RE.search(text)
    if not m:
        return None

    dims = []
    for i in range(1, 7, 2):
        val = float(m.group(i))
        unit = m.group(i+1).lower()
        dims.append(val * UNIT_SCALE[unit])

    return tuple(dims)


def parse_hole(text: str) -> Optional[Dict[str, Any]]:
    m = HOLE_RE.search(text)
    if not m:
        return None

    val = float(m.group(1))
    unit = m.group(2).lower()

    return {
        "type": "hole",
        "diameter": val * UNIT_SCALE[unit]
    }


def parse_relations(text: str) -> Dict[str, Any]:
    rel = {}

    if "center" in text:
        rel["placement"] = "center"

    if "largest face" in text:
        rel["target"] = "largest_face"

    if "top" in text:
        rel["target"] = "top_face"

    return rel

# =========================
# GIBBERISH DETECTION
# =========================

def gibberish_score(tokens: List[str]) -> float:
    if not tokens:
        return 1.0

    valid = sum(1 for t in tokens if t.isalpha() or t.isnumeric())
    return 1 - (valid / len(tokens))

# =========================
# CORE ENGINE
# =========================

class NLPToCAD:

    def parse(self, prompt: str) -> Dict[str, Any]:
        norm = normalize(prompt)
        tokens = tokenize(norm)

        gib = gibberish_score(tokens)

        if gib > 0.7:
            return self._failsafe(prompt, tokens, gib)

        dims = parse_dimensions(norm)
        hole = parse_hole(norm)
        rel = parse_relations(norm)

        entity = None

        if dims:
            entity = {
                "type": "box",
                "dimensions": dims,
                "features": []
            }

        if entity and hole:
            hole["relation"] = rel
            entity["features"].append(hole)

        parts = []

        if entity:
            parts.append({
                "name": "Body",
                "mass": 50.0,
                "position": (0,0,0),
                "attrs": entity
            })

        return {
            "prompt": prompt,
            "normalized": norm,
            "tokens": tokens,
            "gibberish": False,
            "gibberish_score": gib,
            "confidence": 0.9 if entity else 0.4,
            "failsafe": False if entity else True,
            "parts": parts
        }

    def _failsafe(self, prompt, tokens, score):
        return {
            "prompt": prompt,
            "tokens": tokens,
            "gibberish": True,
            "gibberish_score": score,
            "failsafe": True,
            "parts": []
        }

# =========================
# SCRIPT GENERATION
# =========================

def generate_openscad(entity: Dict[str, Any]) -> str:
    dims = entity.get("dimensions")
    features = entity.get("features", [])

    code = []

    if dims:
        x,y,z = dims
        code.append(f"cube([{x},{y},{z}]);")

    for f in features:
        if f["type"] == "hole":
            d = f["diameter"]
            code.append(f"translate([{x/2},{y/2},{z/2}]) cylinder(h={z}, d={d});")

    return "\n".join(code)

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    engine = NLPToCAD()

    test = "Make me a 5 inch by 5 inch by 25 inch box with a hole of 2cm in the center of the largest rectangular face"

    result = engine.parse(test)
    print(result)

    if result["parts"]:
        cad = generate_openscad(result["parts"][0]["attrs"])
        print("\nGenerated CAD:\n", cad)
