import re
from schema import CADPlan, CADPart, Assembly, Constraint


class LLMPlanner:
    """
    Heuristic + LLM-ready planner.
    Deterministic now, language-driven later.
    """

    # -----------------------------
    # PUBLIC API
    # -----------------------------

    def plan(self, prompt: str):
        text = prompt.lower()
        intent = self._infer_intent(text)
        dims = self._extract_dimensions(text)
        constraints = self._extract_constraints(text)

        if intent == "assembly":
            return self._plan_box_assembly(dims, constraints)

        if intent == "prism":
            return CADPlan(
                primitive="prism",
                sides=dims.get("sides", 6),
                radius=dims.get("radius", 20),
                height=dims.get("height", 30),
                notes="Generated prism from prompt"
            )

        # default primitive
        return CADPlan(
            primitive="cube",
            size=dims.get("size", 25),
            fillet=dims.get("fillet", 2),
            notes="Default cube fallback"
        )

    def repair(self, obj, reason: str):
        """
        Targeted repair based on validator / critic feedback
        """
        r = reason.lower()

        if hasattr(obj, "parts"):
            for p in obj.parts:
                self._repair_part(p, r)
        else:
            self._repair_part(obj, r)

        return obj

    # -----------------------------
    # PLANNING HELPERS
    # -----------------------------

    def _infer_intent(self, text: str):
        if any(k in text for k in ["box", "container", "enclosure", "assembly"]):
            return "assembly"
        if "prism" in text or "polygon" in text:
            return "prism"
        return "single"

    def _extract_dimensions(self, text: str):
        dims = {}

        # numbers like "size 40", "radius 10", "height 30"
        for key in ["size", "radius", "height", "fillet"]:
            m = re.search(rf"{key}\s*(\d+)", text)
            if m:
                dims[key] = float(m.group(1))

        # prism sides
        m = re.search(r"(\d+)\s*sided", text)
        if m:
            dims["sides"] = int(m.group(1))

        # hollow intent
        if "hollow" in text:
            dims["hollow"] = True

        return dims

    def _extract_constraints(self, text: str):
        constraints = []

        # mass constraint: "under 500g", "max mass 1000"
        m = re.search(r"(max\s*mass|under)\s*(\d+)", text)
        if m:
            constraints.append(Constraint("max_mass", float(m.group(2))))

        return constraints

    def _plan_box_assembly(self, dims, constraints):
        outer = dims.get("size", 60)
        wall = max(2.0, outer * 0.1)

        parts = [
            CADPart(
                name="outer_shell",
                primitive="cube",
                size=outer,
                fillet=dims.get("fillet", 3),
                notes="Structural shell"
            ),
            CADPart(
                name="inner_cavity",
                primitive="cube",
                size=outer - 2 * wall,
                notes="Hollowed interior"
            )
        ]

        return Assembly(
            parts=parts,
            constraints=constraints or [Constraint("max_mass", 50000)]
        )

    # -----------------------------
    # REPAIR LOGIC
    # -----------------------------

    def _repair_part(self, p, reason: str):
        if "fillet" in reason and p.fillet:
            p.fillet *= 0.5

        elif "mass" in reason or "heavy" in reason:
            if p.size:
                p.size *= 0.9
            if p.primitive == "cylinder":
                p.hollow = True

        elif "dimension" in reason or "size" in reason:
            if p.size:
                p.size *= 0.95
            if p.radius:
                p.radius *= 0.95
            if p.height:
                p.height *= 0.95

        else:
            # conservative fallback
            if p.size:
                p.size *= 0.9