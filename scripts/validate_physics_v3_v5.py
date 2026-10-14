"""Replay the preserved v4 engine against the separately frozen v5 source contract."""

import validate_physics_v3_v4 as engine

engine.CONTRACT = engine.ROOT / "research/physics_v3/validation_v5"

if __name__ == "__main__":
    raise SystemExit(engine.main())
