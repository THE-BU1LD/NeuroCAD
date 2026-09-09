// ========================================
// a 15 x 7 x 0.5 cm plate with four 0.4 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 70, 5], center=true);
  translate([-68, -28, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([-68, 28, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([68, -28, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([68, 28, 0]) {
    cylinder(r=2, h=7, center=true);
  }
}
