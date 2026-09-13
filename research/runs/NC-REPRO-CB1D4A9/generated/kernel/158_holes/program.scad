// ========================================
// a 200 x 80 x 4 mm plate with two 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[200, 80, 4], center=true);
  translate([-92, 0, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([92, 0, 0]) {
    cylinder(r=2, h=6, center=true);
  }
}
