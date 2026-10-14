# External validation successor: NC-PHYS-V3-EXTERNAL-1

Status: PREPARATION ONLY. No measurements, participants or independent executor
have been supplied. This protocol does not alter Physics v2, the terminal
compiler study, or the separately owned `../validation_v1` conformance suite.

## Scope and freeze

Each physical capability gets a separate plan, with exact apparatus, measured
input ranges, units, material identity, reference provenance, tolerances and
uncertainty ceiling. No global physical-accuracy claim is permitted. The six
new scalar models, inherited twelve models, composite geometry/structural
screening, context binding, uncertainty methods and overlays have different
evidence requirements; see CAPABILITIES.json. Unselected capabilities remain
NOT_EVALUATED. Never infer their validity from a selected beam experiment.

Plans in `templates/` deliberately contain nulls. Fill them from real apparatus,
release assets and an identified executor before freezing. A missing value is a
blocker, not an invitation to estimate a result. Freeze the exact procedures,
case IDs, reference files, installed artifact hash and source commit, plus all
thresholds before opening outcomes. Outcome-driven tolerance changes require a
new version, new cases and retention of the original failure. The audit script
hash is bound at freeze. Archive the full frozen package with the investigator
and external executor; the local timestamp is not an independent timestamp.

All frozen case IDs must appear in results, including FAIL and BLOCKED. No
outcome-based exclusions, replacement participants or dropped instrument runs.
Repeat or corrective studies have new IDs and preserve the first outcome.
No purchasing, participant contact or experiment execution is performed by this
package. Instrument selection and experiment operating limits require the
responsible experimenter's documented review before collection.

## Physical campaigns

### Beam deflection

Use a measured prismatic beam in the elastic, slender, small-deflection regime.
Record specimen material/source, width, thickness, span, clamp geometry, load
position and instrument resolution. Determine modulus from a separate source
or independent coupon test, not by fitting the validation deflections. Include
zero-load, at least three predeclared nonzero loads and an unload check, with
three independent load/unload cycles at each condition. Measure fixture motion
and zero drift. Predict tip deflection before opening the corresponding readings.
Document why shear deformation and clamp compliance are negligible or explicitly
exclude the resulting claim. Do not load to buckling, yield or fracture for this
screening validation. Freeze actual loads and limits with the experimenter.

### Thermal response

Use a temperature range and specimen compatible with the selected steady
conduction, thermal-network or lumped-transient model. Record sensor positions,
calibration at multiple temperatures, ambient conditions, contact resistances,
heat losses and boundary stability. For transient work, establish the Biot
criterion independently and freeze the sampling times. Do not fit heat-transfer
parameters to the same validation trace. Retain the entire time series, including
warm-up and non-equilibrium periods. Three repeated trials per predeclared
condition; blocked or unstable equilibrium stays in the record.

### Vibration

Use a documented linear single-mode fixture. Independently determine mass,
stiffness and damping; do not fit them to the validation frequency sweep. Freeze
frequencies below, around and above the estimated natural frequency, excitation
amplitudes, steady-state criterion, sampling rate and sensor calibration. Retain
time histories and amplitude extraction code. Three independent sweeps; report
additional modes, nonlinearity and fixture motion as applicability failures.

### Pipe pressure loss

Use measured internal diameter, length, roughness, fluid temperature, density
and viscosity, flow-meter calibration, pressure-tap locations and pressure
sensor calibration. Separate entry/minor losses from the claimed major-loss
model. Start with a predeclared laminar range; freeze flow rates and three
independent trials per condition. Any turbulent-factor campaign needs a source
for friction factors independent of its validation pressure measurements.
Do not infer general network or turbulence validity from a straight-pipe test.

For every campaign, the registered operator supplies apparatus limits, numerical
acceptance thresholds and the measurable applicability envelope before freeze.
No experiment is executable from this draft alone.

### Numerical scoring

Use absolute error `abs(predicted - measured)` and tolerance
`atol + rtol * abs(measured)` in the frozen units. Pass a case only when the
error meets that tolerance AND its expanded measurement uncertainty is below
the independently chosen ceiling. Record the coverage factor and uncertainty
budget (calibration, repeatability, resolution, geometry, alignment, environment,
input correlations). Propagate model-input uncertainty separately from measurement
uncertainty; explain correlations and whether either includes shared calibration.
Report signed bias and every trial, not only averages. The script compares
declared numbers but cannot establish calibration validity or truthful collection.

## Independent reproduction

Choose an executor outside implementation; record contributions/conflicts and
their signed declaration. Send the frozen scalar/workflow package, exact public
wheel hash, source commit, lockfiles, expected tolerances and documented commands.
They install in a new environment outside the checkout, record OS/Python/tools,
installed module paths, dependencies, commands, stdout/stderr and exit statuses,
and attempt every frozen case exactly once before troubleshooting. They retain
failures and write their own discrepancy report. Missing dependencies are BLOCKED,
not correct model rejection. Assistance and subsequent fixes are recorded as
separate attempts. A second run by the implementer is not independent reproduction.

The external executor independently checks reference derivations and provenance;
replaying project-authored expected values alone does not close the independent
calculation gate. Include limit/invalid/instability cases and installed workflows.

## Intended-user evaluation

Use at least five eligible users for a formative study, with recruitment criteria
fixed before results. This is a defect-finding study, not a population usability
estimate. Obtain consent, assign pseudonymous IDs, keep identifying consent
documents outside the repository, and retain a permission receipt only. Exclude
implementers from intended-user counts. Record withdrawals without fabricating
task results. Freeze the completion rubric and assistance rule before sessions.

Tasks: create a supported complex part from dimensions; assign a sourced material
at a supported temperature; define a load and combination with explicit units;
run and explain an analytical result; change a bound input and detect a stale
result; inspect uncertainty and distinguish a scalar overlay from a spatial
simulation; reject an unsupported request. Use the installed release.

Record per participant/task elapsed time, assistance, errors, task outputs, correct
load/material specification, interpretation of limits and screening versus
validated predictions. A task passes this conservative formative gate only if
every enrolled eligible participant completes without help and meets all rubric
items. Report failures directly; repair defects and run a separately identified
follow-up, never replace the original observations. Maintain worked examples in
public documentation after testing them against the same release.

## Closing a gate

`evidence.py` only checks required fields, hashes, coverage and numeric criteria.
EVIDENCE_COMPLETE_REVIEW_REQUIRED is NOT physical validation, independent
reproduction or usability certification. A named reviewer must inspect raw
evidence, independence, calibration, uncertainty and applicability, sign a
capability-specific decision, and link it from canonical state. No automatic
script promotes a scientific gate. Failed complete studies remain valid negative
evidence; incomplete studies remain blocked.
