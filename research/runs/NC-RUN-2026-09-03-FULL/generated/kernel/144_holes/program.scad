// ========================================
// a 140 x 130 x 5 mm plate with three 8 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[140, 130, 5], center=true);
  translate([-57, -52, 0]) {
    cylinder(r=4, h=7, center=true);
  }
  translate([57, -52, 0]) {
    cylinder(r=4, h=7, center=true);
  }
  translate([0, 52, 0]) {
    cylinder(r=4, h=7, center=true);
  }
}
