// ========================================
// a 60 x 140 x 2 mm plate with two 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[60, 140, 2], center=true);
  translate([-24, 0, 0]) {
    cylinder(r=1.5, h=4, center=true);
  }
  translate([24, 0, 0]) {
    cylinder(r=1.5, h=4, center=true);
  }
}
