// ========================================
// a 15 x 7 x 0.5 cm plate with two 1.6 x 0.2 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 70, 5], center=true);
  translate([-59, 0, 0]) {
    cube(size=[16, 2, 7], center=true);
  }
  translate([59, 0, 0]) {
    cube(size=[16, 2, 7], center=true);
  }
}
