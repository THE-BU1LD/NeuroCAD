# NeuroCAD IR grammar and semantic rules

The JSON Schema is normative for surface syntax. This compact EBNF documents structure; it is not a second parser.

```ebnf
program     = version, units, title, node-list, root-list, constraint-list, metadata ;
version     = "neurocad-ir-v1" ;
units       = "mm" ;
node        = primitive-node | composition-node ;
primitive-node = id, primitive, transform, role ;
composition-node = id, composition, child-list, transform, role ;
primitive   = box | rounded-box | sphere | cylinder | cone | torus ;
composition = "union" | "difference" | "intersection" ;
transform   = translate-vec3, rotate-vec3, scale-vec3 ;
constraint  = dimension | coincident | offset | child-count | bounds ;
reference   = id ;
```

Semantic invariants: IDs are unique; every reference resolves; roots exist; compositions have children; the graph is acyclic and has at most 1,024 nodes and depth 128; dimensions are finite and satisfy primitive-specific positivity/shape conditions; scales are finite and non-zero; declared constraints must evaluate true. The compiler rejects violations before recursive bounds or OpenSCAD export.

The prompt frontend is deliberately separate. It recognizes fully dimensioned plates/boxes/open-top enclosures, cylinders, spheres, circular holes, and rectangular slots. Supported length units normalize to millimetres. Missing required dimensions, unsupported domains, excessive feature counts, and ambiguous incomplete prompts fail closed.

