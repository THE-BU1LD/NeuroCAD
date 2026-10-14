# Retained defect: opposing loads hide an interior maximum

Frozen case: `beam-opposed`, NC-PHYS-V3-CONFORMANCE-1.
Source receipt: `source-scalar-01/receipt.json`.

Inputs: L=120 mm, E=70,000 MPa, I=6,000 mm^4, section modulus
Z=600 mm^3, tip force F=-42 N, uniform load w=0.7 N/mm.

Let z be distance from the free end. Equilibrium gives
M(z)=F*z+w*z^2/2=-42*z+0.35*z^2 N mm on 0 <= z <= 120.
Both endpoint moments vanish. The interior stationary point is z=60 mm,
where M=-1260 N mm. Therefore the maximum absolute bending stress is
1260/600=2.1 MPa. The implementation uses only the fixed-end moment and
reports 0 MPa. Its tip deflection and fixed-end shear match the references.

This is a source-level mathematical counterexample inside the declared signed
tip/uniform-load contract, not a physical experiment. The defect can also
understate yield utilization when a yield strength is supplied; that consequence
is inferred from the implementation, not an additional executed frozen case.

Do not promote the complete v3 analytical contract to validated status.
A correction must consider endpoints and any interior moment extremum, retain
this failure and use a separately versioned source/freeze. Replaying this known
case after a fix establishes regression conformance, not independent validation.
No production source was changed by this validation task.
