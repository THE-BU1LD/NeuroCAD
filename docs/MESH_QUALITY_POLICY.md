# Mesh quality acceptance policy

The supervised STEP mesher can require a caller-selected minimum SICN element
quality score before publishing a mesh bundle:

```bash
neurocad-mesh step design.step --output-dir new-mesh --max-size 3 --minimum-sicn 0.1
```

The threshold must be finite and in (0, 1]. Equality passes. Quality below the
threshold, or unavailable quality, fails explicitly and publishes no bundle.
The input STEP remains unchanged. Accepted policies record the metric, threshold,
observed score and decision in `execution-receipt.json`, bound to the existing
STEP, mesh and meshing-receipt hashes.

Omitting the option preserves the existing serialization acceptance behavior.
There is no universal default threshold: select it for a declared downstream
use. A passing quality floor does not establish solver convergence, accuracy,
physical validity, manufacturability or safety. This gate does not heal CAD or
silently remesh with different settings to pass the requested policy.
