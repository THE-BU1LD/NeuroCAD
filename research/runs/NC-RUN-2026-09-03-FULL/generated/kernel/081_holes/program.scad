// ========================================
// a 9 x 6 x 0.4 cm plate with five 0.2 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 60, 4], center=true);
  translate([-39, -24, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([0, -24, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([39, -24, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([-39, 24, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([0, 24, 0]) {
    cylinder(r=1, h=6, center=true);
  }
}
