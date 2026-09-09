// ========================================
// a 190 x 110 x 5 mm plate with three 10 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 110, 5], center=true);
  translate([-85, -45, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
  translate([85, -45, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
  translate([0, 45, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
}
