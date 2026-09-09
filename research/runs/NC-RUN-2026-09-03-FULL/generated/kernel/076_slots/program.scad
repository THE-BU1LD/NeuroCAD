// ========================================
// a 240 x 80 x 3 mm plate with four 10 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[240, 80, 3], center=true);
  translate([-110, -30, 0]) {
    cube(size=[10, 5, 5], center=true);
  }
  translate([-110, 30, 0]) {
    cube(size=[10, 5, 5], center=true);
  }
  translate([110, -30, 0]) {
    cube(size=[10, 5, 5], center=true);
  }
  translate([110, 30, 0]) {
    cube(size=[10, 5, 5], center=true);
  }
}
