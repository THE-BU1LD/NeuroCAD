# Five-minute NeuroCAD demo

This demo proves the bounded product contract; it does not claim general CAD,
manufacturability, native third-party integration, or physical fit.

## Before the call

Use CPython 3.10-3.12 and install OpenSCAD so `openscad --version` works. Install
NeuroCAD from the candidate wheel or an obtained source checkout, then run:

```bash
demo/build_demo_kit.sh neurocad-demo-artifacts
```

The destination must be new. Success produces three worked examples, verified
STLs, editable SCAD/IR, manifests, a deliberate rejection, and
`DEMO_RECEIPT.json` with byte counts, artifact hashes, and the source identity
reported by the executing `NEUROCAD_CLI`. The script requests `provenance --json`
before and after the demo and refuses a success receipt if those identities differ.
`PYTHON_BIN` only writes the receipt; an unrelated NeuroCAD installation visible to
that interpreter cannot supply the identity. The two identity snapshots are retained.

The identity hashes the executing CLI source, `text_to_cad.py`,
`text_to_openscad.py`, all Python, JSON and JavaScript files under its active
`core` package, and the packaged JavaScript license. File names use stable relative
paths. Absolute installation paths and timestamps are excluded. This is an on-disk
source/resource snapshot; it does not attest loaded bytecode, third-party dependencies,
or an unchanged implementation between the two observations. In particular, a
transient change followed by restoration is outside this check.

When the CLI source is at a Git checkout root, the receipt also records observed
HEAD metadata as `observed_checkout`. That metadata never proves that source bytes
match the commit, including in a modified checkout. For an installed package without
that checkout metadata, the revision is explicitly unavailable.

To annotate an installed-package run with a reviewed source commit, supply that
full commit explicitly:

```bash
NEUROCAD_SOURCE_REVISION="$(git rev-parse HEAD)" \
  demo/build_demo_kit.sh neurocad-demo-artifacts
```

Only use a commit you have independently reviewed; this variable is recorded in
the receipt as `user_supplied_unverified`. It does not validate a release, prove
that an installed package came from that commit, or change the generated geometry.

## Live script

1. **0:00-0:30 — Set the boundary.** “NeuroCAD is a deterministic compiler for
   explicitly dimensioned plates, primitives, and electronics enclosures. It is
   not a general CAD model, simulator, or fabrication approval system.”
2. **0:30-1:30 — Fail closed.** Run
   `neurocad validate "design a load-rated aircraft engine mount"`. Show the
   nonzero rejection and explain that missing or unsupported geometry is never
   invented.
3. **1:30-2:30 — Plate.** Validate and create the 120 x 80 x 4 mm four-hole
   plate. Open the generated JSON and SCAD, then show the verified STL result.
4. **2:30-3:15 — Primitive.** Generate the radius-20-by-height-50 mm cylinder.
   Point out the 40 x 40 x 50 mm verified mesh extents.
5. **3:15-4:30 — Enclosure.** Interpret the semicolon-delimited USB-C enclosure,
   then show the project, body/lid SCAD, mesh verification, and cutout probe.
6. **4:30-5:00 — Ask for one real workflow.** Capture the user's prompt,
   expected geometry, acceptable exchange format, and biggest failure. Do not
   claim a successful trial until they run it on their own design.

## Platform truth

- The package targets CPython 3.10, 3.11, and 3.12.
- Kernel-independent tests are configured for Ubuntu 24.04, macOS 15, and
  Windows Server 2025; external CI evidence is still required for a public
  release.
- STL compilation requires OpenSCAD. The checked-in release workflow uses
  Ubuntu with Xvfb; the local execution audit also verifies CLI STL export on
  macOS.
- Physical printing and fit testing remain pending until the physical
  validation protocol is completed.

Use the repository issue form for trial feedback. Preserve the generated
receipt when reporting a failure so the exact artifacts can be identified.
