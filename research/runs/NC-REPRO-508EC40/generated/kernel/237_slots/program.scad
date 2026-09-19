// ========================================
// a 220 x 80 x 5 mm plate with four 20 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[220, 80, 5], center=true);
  translate([-90, -20, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
  translate([-90, 20, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
  translate([90, -20, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
  translate([90, 20, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
}
