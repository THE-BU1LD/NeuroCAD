from planner import LLMPlanner
from validator import PlanValidator
from geometry import generate_scad


def run_cli():
    planner = LLMPlanner()
    validator = PlanValidator()

    print("🧠 CAD Agent")
    print("Describe an object (type 'exit' to quit)")

    while True:
        prompt = input("> ").strip()
        if prompt.lower() in {"exit", "quit"}:
            break

        try:
            plan = planner.plan(prompt)
            validator.validate(plan)

            scad = generate_scad(plan)

            with open("output.scad", "w") as f:
                f.write(scad)

            print("✅ Generated output.scad")

        except Exception as e:
            print(f"❌ {e}")