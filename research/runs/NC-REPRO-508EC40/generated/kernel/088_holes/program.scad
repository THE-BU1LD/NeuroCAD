// ========================================
// a 130 x 70 x 2 mm plate with two 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[130, 70, 2], center=true);
  translate([-58, 0, 0]) {
    cylinder(r=2, h=4, center=true);
  }
  translate([58, 0, 0]) {
    cylinder(r=2, h=4, center=true);
  }
}
