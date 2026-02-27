
// ==========================================
// GENERATED AIRCRAFT VARIANT 1
// ==========================================

$fn = 90;

// --------- FUSELAGE ----------
module fuselage() {
    cylinder(h=1.1025,
             r1=0.09056249999999999,
             r2=0.07875,
             center=false);
}

// --------- WING ----------
module wing_half(sign=1) {
    rotate([0, 5*sign, 0])
    translate([0, sign*0.77175, 0])
    cube([0.25725000000000003,
          0.77175,
          0.018375000000000002],
          center=true);
}

module wing() {
    wing_half(1);
    wing_half(-1);
}

// --------- TAIL ----------
module tail() {
    translate([0, 0, 0.937125])
    cube([0.11576250000000002,
          0.540225,
          0.0128625],
          center=true);
}

module vertical_tail() {
    translate([0, 0, 0.9702000000000001])
    rotate([90,0,0])
    cube([0.09261000000000003,
          0.0128625,
          0.2701125],
          center=true);
}

union() {
    fuselage();
    translate([0,0,0.49612500000000004]) wing();
    tail();
    vertical_tail();
}
