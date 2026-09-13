// ========================================
// a 18 x 9 x 0.5 cm plate with four 0.5 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[180, 90, 5], center=true);
  translate([-81, -36, 0]) {
    cylinder(r=2.5, h=7, center=true);
  }
  translate([-81, 36, 0]) {
    cylinder(r=2.5, h=7, center=true);
  }
  translate([81, -36, 0]) {
    cylinder(r=2.5, h=7, center=true);
  }
  translate([81, 36, 0]) {
    cylinder(r=2.5, h=7, center=true);
  }
}
