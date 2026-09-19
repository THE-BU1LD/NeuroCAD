// ========================================
// a 110 x 70 x 2 mm plate with four 16 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 70, 2], center=true);
  translate([-39, -19, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
  translate([-39, 19, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
  translate([39, -19, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
  translate([39, 19, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
}
