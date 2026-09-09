// ========================================
// a 8 x 17 x 0.5 cm plate with two 0.8 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[80, 170, 5], center=true);
  translate([-32, 0, 0]) {
    cylinder(r=4, h=7, center=true);
  }
  translate([32, 0, 0]) {
    cylinder(r=4, h=7, center=true);
  }
}
