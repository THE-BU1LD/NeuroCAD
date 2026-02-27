
// ==========================================
// GENERATED AIRCRAFT VARIANT 0
// ==========================================

$fn = 90;

// --------- FUSELAGE ----------
module fuselage() {
    cylinder(h=1.05,
             r1=0.08625,
             r2=0.075,
             center=false);
}

// --------- WING ----------
module wing_half(sign=1) {
    rotate([0, 4*sign, 0])
    translate([0, sign*0.7087500000000001, 0])
    cube([0.23625000000000004,
          0.7087500000000001,
          0.016875000000000005],
          center=true);
}

module wing() {
    wing_half(1);
    wing_half(-1);
}

// --------- TAIL ----------
module tail() {
    translate([0, 0, 0.8925])
    cube([0.10631250000000002,
          0.49612500000000004,
          0.011812500000000002],
          center=true);
}

module vertical_tail() {
    translate([0, 0, 0.924])
    rotate([90,0,0])
    cube([0.08505000000000001,
          0.011812500000000002,
          0.24806250000000002],
          center=true);
}

union() {
    fuselage();
    translate([0,0,0.47250000000000003]) wing();
    tail();
    vertical_tail();
}
