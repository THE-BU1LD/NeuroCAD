
// ==========================================
// GENERATED AIRCRAFT VARIANT 2
// ==========================================

$fn = 90;

// --------- FUSELAGE ----------
module fuselage() {
    cylinder(h=1.1550000000000002,
             r1=0.09487500000000001,
             r2=0.08250000000000002,
             center=false);
}

// --------- WING ----------
module wing_half(sign=1) {
    rotate([0, 6*sign, 0])
    translate([0, sign*0.8373750000000003, 0])
    cube([0.2791250000000001,
          0.8373750000000003,
          0.019937500000000007],
          center=true);
}

module wing() {
    wing_half(1);
    wing_half(-1);
}

// --------- TAIL ----------
module tail() {
    translate([0, 0, 0.9817500000000002])
    cube([0.12560625000000006,
          0.5861625000000001,
          0.013956250000000003],
          center=true);
}

module vertical_tail() {
    translate([0, 0, 1.0164000000000002])
    rotate([90,0,0])
    cube([0.10048500000000005,
          0.013956250000000003,
          0.29308125000000007],
          center=true);
}

union() {
    fuselage();
    translate([0,0,0.5197500000000002]) wing();
    tail();
    vertical_tail();
}
