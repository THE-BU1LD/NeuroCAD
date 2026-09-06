// ========================================
// a 170 x 150 x 2 mm plate with two 6 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[170, 150, 2], center=true);
  translate([-70, 0, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([70, 0, 0]) {
    cylinder(r=3, h=4, center=true);
  }
}
