// ========================================
// a 150 x 160 x 5 mm plate with four 20 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 160, 5], center=true);
  translate([-55, -60, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
  translate([-55, 60, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
  translate([55, -60, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
  translate([55, 60, 0]) {
    cube(size=[20, 5, 7], center=true);
  }
}
