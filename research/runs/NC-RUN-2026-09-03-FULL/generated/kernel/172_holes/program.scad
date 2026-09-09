// ========================================
// a 16 x 8 x 0.3 cm plate with five 0.3 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 80, 3], center=true);
  translate([-72, -32, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([0, -32, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([72, -32, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-72, 32, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([0, 32, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
}
