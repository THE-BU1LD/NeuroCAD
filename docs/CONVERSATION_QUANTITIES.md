# Explicit quantity edits

The local enclosure editor accepts complete scalar clauses with an explicit unit (mm, cm, inches, or their spelled-out names):

- `make the walls three millimeters thick`
- `set lid clearance to zero point four mm`
- `add one millimeter to the wall thickness`
- `decrease wall thickness by 0.5 mm`
- `make the power hole radius 3mm`

Number words cover zero through ninety-nine, including `twenty-one` and `twenty one`. Spoken decimals use individual digits, such as `three point one two five`. Decimal arithmetic resolves unit conversion and relative quantities before conversion to the stored numeric representation.

Relative edits use the current project revision. Review the resulting absolute value before applying the proposal. A proposal cannot be reapplied after the project changes. Multiple edits to the same scalar involving a relative quantity require a single explicit final value.

Radius wording requires a uniquely named existing circular cutout. A 3 mm radius becomes a 6 mm diameter; the feature ID and position remain unchanged. Ambiguous names, rectangular cutouts, missing units, negative results, conflicting instructions and unsupported clauses yield no candidate.

This grammar does not resolve conversation history, fractions such as “one and a half”, number words above ninety-nine, or arbitrary fragmented instructions. Quantity edits retain the existing specification validation and review requirements. They do not certify the exported geometry or physical performance.

[Implementation and measured limits](../research/development/conversation_quantities_20261015/REPORT.md).

[Scalar preservation, only-scope and explicit correction rules](SCALAR_INTENT.md) extend these quantities while retaining the original review and context checks.
