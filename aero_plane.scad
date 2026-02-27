
// ================================
// GENERATED AERODYNAMIC AIRCRAFT
// ================================

$fn = 80;

// --------- FUSELAGE ----------
module fuselage() {
    scale([1, 1, 1])
        cylinder(h=1.12,
                 r1=0.096,
                 r2=0.08,
                 center=false);
}

// --------- WING ----------
module wing_half(sign=1) {
    rotate([0, 6*sign, 0])
    translate([0, sign*0.784, 0])
    cube([0.26133333333333336,
          0.784,
          0.018666666666666668],
          center=true);
}

module wing() {
    wing_half(1);
    wing_half(-1);
}

// --------- TAIL ----------
module tail() {
    translate([0, 0, 0.9520000000000001])
    cube([0.11760000000000001,
          0.5488,
          0.013066666666666667],
          center=true);
}

module vertical_tail() {
    translate([0, 0, 0.9856000000000001])
    rotate([90,0,0])
    cube([0.09408000000000001,
          0.013066666666666667,
          0.2744],
          center=true);
}

// --------- ASSEMBLY ----------
union() {
    fuselage();
    translate([0,0,0.5040000000000001]) wing();
    tail();
    vertical_tail();
}
