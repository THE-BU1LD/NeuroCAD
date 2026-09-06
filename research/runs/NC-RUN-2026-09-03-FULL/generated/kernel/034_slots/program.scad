// ========================================
// a 240 x 120 x 5 mm plate with four 10 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[240, 120, 5], center=true);
  translate([-110, -50, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
  translate([-110, 50, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
  translate([110, -50, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
  translate([110, 50, 0]) {
    cube(size=[10, 2, 7], center=true);
  }
}
