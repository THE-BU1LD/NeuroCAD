import traceback
import os

TESTS = [
    "test_cadify.py",
    "test_regression.py",
]

def run():
    for t in TESTS:
        if not os.path.exists(t):
            print(f"⚠️  Skipping {t} (not found)")
            continue

        print(f"\n=== RUNNING {t} ===")
        try:
            exec(open(t).read(), {})
            print(f"✅ {t} PASSED")
        except Exception:
            print(f"❌ {t} FAILED")
            traceback.print_exc()

if __name__ == "__main__":
    run()
