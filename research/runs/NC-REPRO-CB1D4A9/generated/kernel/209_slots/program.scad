// ========================================
// a 110 x 140 x 4 mm plate with two 20 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 140, 4], center=true);
  translate([-35, 0, 0]) {
    cube(size=[20, 2, 6], center=true);
  }
  translate([35, 0, 0]) {
    cube(size=[20, 2, 6], center=true);
  }
}
