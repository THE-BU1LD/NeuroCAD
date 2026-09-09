// ========================================
// a 230 x 170 x 3 mm plate with three 10 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[230, 170, 3], center=true);
  translate([-105, -75, 0]) {
    cube(size=[10, 4, 5], center=true);
  }
  translate([105, -75, 0]) {
    cube(size=[10, 4, 5], center=true);
  }
  translate([0, 75, 0]) {
    cube(size=[10, 4, 5], center=true);
  }
}
