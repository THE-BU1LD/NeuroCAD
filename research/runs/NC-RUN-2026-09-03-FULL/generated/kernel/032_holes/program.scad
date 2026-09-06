// ========================================
// a 24 x 16 x 0.2 cm plate with five 0.6 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[240, 160, 2], center=true);
  translate([-104, -64, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([0, -64, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([104, -64, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([-104, 64, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([0, 64, 0]) {
    cylinder(r=3, h=4, center=true);
  }
}
