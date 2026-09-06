// ========================================
// a 200 x 80 x 2 mm plate with two 10 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[200, 80, 2], center=true);
  translate([-90, 0, 0]) {
    cube(size=[10, 2, 4], center=true);
  }
  translate([90, 0, 0]) {
    cube(size=[10, 2, 4], center=true);
  }
}
