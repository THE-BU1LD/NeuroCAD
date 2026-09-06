// ========================================
// a 110 x 60 x 2 mm plate with two 8 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 60, 2], center=true);
  translate([-47, 0, 0]) {
    cylinder(r=4, h=4, center=true);
  }
  translate([47, 0, 0]) {
    cylinder(r=4, h=4, center=true);
  }
}
