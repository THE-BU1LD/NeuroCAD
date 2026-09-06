// ========================================
// a 210 x 170 x 4 mm plate with two 10 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[210, 170, 4], center=true);
  translate([-95, 0, 0]) {
    cube(size=[10, 5, 6], center=true);
  }
  translate([95, 0, 0]) {
    cube(size=[10, 5, 6], center=true);
  }
}
