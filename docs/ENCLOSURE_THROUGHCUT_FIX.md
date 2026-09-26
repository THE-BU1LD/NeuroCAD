# Enclosure through-cut correction

## Reproduced failure

The enclosure's side/floor cut tool used depth `t + 2 mm` but was centered on
the outer surface. Its inward reach was therefore `(t + 2)/2`, not the full
material thickness `t`. For `t > 2 mm`, the uncut inner cap was `(t - 2)/2`.
A supported 2.0 to 2.4 mm wall edit left a 0.2 mm cap behind a connector opening.
The old center-only void probe still passed: checking a cavity at half depth
was not sufficient to establish an opening through the wall.

An analogous lid cut was centered at z=0 rather than at the center of the
plate-plus-plug span. A friction-lid lip taller than 2 mm could leave a blind
cap. Existing fastener cutter placement was already centered correctly.

## Correction

Body circular/rectangular cutouts and vents now center the cutter halfway
through the selected wall or floor. The original depth remains `t + 2 mm`,
providing 1 mm nominal overtravel at each surface. Lid cutouts are centered at
`-lip_height/2`, through the full plate-plus-lip span. No primitive dimensions,
request grammar, tolerances, scientific protocol, or meshing backend are changed.

Independent mesh probes retain the previous center and adjacent-material
checks, and add probes at 2% and 98% through the relevant material span.
The verification method is now `independent-ray-parity-through-thickness-v2`.
These finite probes detect the reproduced blind caps. They do not prove every
point of an arbitrary cut is clear and are not a tolerance, manufacturing,
structural-safety, or physical-fit certification.

## Verification and compatibility

The new test module contains 54 kernel-independent placement contracts and
8 real OpenSCAD regression cases spanning all five body faces, lids, circular
and rectangular openings, and vents. Each native case constructs both the
corrected geometry and a deliberately restored legacy cutter placement.
The old non-depth probes pass on that legacy geometry; the added inner-depth
probe rejects it. All 8 corrected native fixtures pass the new checks.

Together with existing enclosure product, edit-language and CLI tests, the
local focused run passed 95 cases with no errors, failures or skips. Native
execution used OpenSCAD 2021.01. This is engineering regression evidence, not a
new scientific evaluation or independent manufacturing validation.

Canonical cutter transforms and verification metadata change for affected
inputs. Regenerate into a **new output directory** to obtain corrected meshes
and current receipts; do not rewrite or relabel previously accepted artifacts.
Keep historical failed/false-accepted fixtures as failure evidence.

The accompanying synthetic 80 x 60 x 30 mm enclosure demo was regenerated with
this repair: original wall 2 mm, edited wall 2.4 mm, and a 40 mm invalid wall
request rejected without writing a replacement. The connector dimensions are
illustrative, not a certified hardware interface. Neither the demo nor a green
test suite authorizes printing, manufacturing, release, merge or deployment.
