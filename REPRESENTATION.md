# Canonical representation

`neurocad-ir-v1` is a directed acyclic CAD program graph serialized as JSON. The normative machine schema is `core/schemas/neurocad_ir_v1.schema.json`; semantic rules are implemented in `core/ir.py`.

A program contains a schema version, millimetre unit declaration, title, uniquely identified nodes, root references, constraints, and metadata. A node is exactly one of a primitive leaf or a Boolean composition. Primitives are `box`, `rounded_box`, `sphere`, `cylinder`, `cone`, and `torus`. Compositions are `union`, `difference`, and `intersection`. Every node carries translation, XYZ Euler rotation, and non-zero scale. Constraints are `dimension`, `coincident`, `offset`, `child_count`, and `bounds`.

Validation proceeds in fixed stages: JSON decoding and size/depth limits; Draft 2020-12 schema/type validation; unique-ID and reference resolution; DAG and parent checks; primitive and transform domain checks; constraint evaluation; deterministic OpenSCAD construction. Errors carry stable stage/category/path information through `IRParseError` or validation records. Serialization sorts keys and normalizes tuples to JSON arrays, enabling exact parse/serialize round trips.

Editability means a named parameter can be changed in the program and the result revalidated, serialized, parsed, and exported. It does not mean a human study has established ergonomic usability.

