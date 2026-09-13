// ========================================
// a 70 x 160 x 3 mm plate with two 5 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[70, 160, 3], center=true);
  translate([-28, 0, 0]) {
    cylinder(r=2.5, h=5, center=true);
  }
  translate([28, 0, 0]) {
    cylinder(r=2.5, h=5, center=true);
  }
}
