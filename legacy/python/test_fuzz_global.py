import random
import string
import traceback
from main import CADPart, Assembly, Constraint

PRIMITIVES = ["cube", "cylinder", "sphere", "cone", "nose", "invalid"]
MATERIALS = ["PLA", "ABS", "PETG", "STEEL", None]
BOOLS = [True, False]

def rand_name():
    return "".join(random.choices(string.ascii_lowercase, k=6))

def fuzz_part():
    prim = random.choice(PRIMITIVES)

    return CADPart(
        name=rand_name(),
        primitive=prim,
        size=random.choice([None, random.uniform(-5, 20)]),
        radius=random.choice([None, random.uniform(-5, 10)]),
        height=random.choice([None, random.uniform(-5, 30)]),
        hollow=random.choice(BOOLS),
        wall_thickness=random.choice([None, random.uniform(-2, 5)]),
        material=random.choice(MATERIALS),
        streamlined=random.choice(BOOLS),
        fillet=random.choice([0, 0.5, 1.0])
    )

def fuzz():
    failures = 0

    for i in range(300):
        try:
            p = fuzz_part()
            p.validate()

            a = Assembly(
                name="A",
                parts=[p],
                constraints=[Constraint("mass", random.uniform(0, 1000))]
            )
            a.validate()

        except ValueError:
            pass  # expected
        except Exception as e:
            failures += 1
            print("\n🔥 UNEXPECTED FAILURE")
            traceback.print_exc()

    print(f"\nFuzz complete — unexpected failures: {failures}")

if __name__ == "__main__":
    print("\n=== FUZZ TESTING CADIFY ===\n")
    fuzz()
