// ========================================
// a 16 x 8 x 0.2 cm plate with three 1.6 x 0.3 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 80, 2], center=true);
  translate([64, 0, 0]) {
    cube(size=[16, 3, 4], center=true);
  }
  translate([-32, 20.7846096908265, 0]) {
    cube(size=[16, 3, 4], center=true);
  }
  translate([-32, -20.7846096908265, 0]) {
    cube(size=[16, 3, 4], center=true);
  }
}
