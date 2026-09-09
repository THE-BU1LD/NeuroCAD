# Physical enclosure validation protocol

This protocol defines the evidence required before calling a NeuroCAD enclosure
fit-checked or fabrication-ready. It contains no experimental results.

## Frozen inputs

Record before printing:

- exact Git commit and clean-tree status;
- project JSON SHA-256 and revision;
- verified exchange-manifest SHA-256;
- source KiCad board SHA-256 when applicable;
- printer, nozzle, firmware, slicer/version, material vendor/lot, layer height,
  temperature, orientation, support, and infill settings;
- caliper resolution and calibration date;
- the acceptance criteria below.

Changing any frozen item creates a new validation series. Failed prints and
measurements remain in the record.

## Minimum evidence

Use at least three independently started print runs spanning at least two days.
Each run must include an XYZ coupon, three vertical/horizontal hole sizes, the
friction-clearance ladder when a friction lid is used, and one complete
enclosure. Reprinting from the same still-warm build plate is not an independent
run.

For every observation record a stable specimen ID, run ID, nominal value,
measured value, measurement resolution, and failure notes. Feed coupon data to
`neurocad calibration fit`; never enter desired derived values directly.

## Predeclared acceptance criteria

- No crack, delamination, missing wall, blocked cutout, or unintended detached
  body in any accepted enclosure.
- Each critical PCB/cutout coordinate is within the larger of 0.20 mm or the
  predeclared hardware-specific tolerance.
- The actual PCB seats without forced bending and every intended mounting hole
  aligns with its explicitly designed standoff.
- Connectors mate through their cutouts without loading the PCB or enclosure.
- A friction lid must assemble and disassemble for ten cycles without fracture
  or unintended release; a screw lid must accept the declared hardware without
  stripping during the declared torque procedure.
- All failures count. A series passes only when every hard criterion passes in
  all three runs.

This protocol does not establish safety, regulatory compliance, structural
rating, ingress protection, or material suitability.

## Required retained artifacts

Retain the frozen inputs, raw observation JSON, fitted calibration profile,
`neurocad enclosure preflight` output, `neurocad integrations verify` output,
STLs, slicer project/G-code, photographs, measurement table, failures, and a
signed reviewer conclusion. Hash every retained file in a generated manifest.

Until those records exist, documentation must say "kernel verified, physical
validation pending" rather than "manufacturing validated".
