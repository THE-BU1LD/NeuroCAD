// ========================================
// a 150 x 60 x 4 mm plate with four 10 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 60, 4], center=true);
  translate([-65, -20, 0]) {
    cube(size=[10, 5, 6], center=true);
  }
  translate([-65, 20, 0]) {
    cube(size=[10, 5, 6], center=true);
  }
  translate([65, -20, 0]) {
    cube(size=[10, 5, 6], center=true);
  }
  translate([65, 20, 0]) {
    cube(size=[10, 5, 6], center=true);
  }
}
