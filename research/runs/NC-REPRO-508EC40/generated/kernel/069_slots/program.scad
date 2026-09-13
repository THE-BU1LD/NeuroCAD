// ========================================
// a 240 x 160 x 2 mm plate with two 20 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[240, 160, 2], center=true);
  translate([-100, 0, 0]) {
    cube(size=[20, 4, 4], center=true);
  }
  translate([100, 0, 0]) {
    cube(size=[20, 4, 4], center=true);
  }
}
