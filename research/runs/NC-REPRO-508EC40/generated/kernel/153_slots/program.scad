// ========================================
// a 17 x 15 x 0.4 cm plate with three 1.6 x 0.4 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[170, 150, 4], center=true);
  translate([69, 0, 0]) {
    cube(size=[16, 4, 6], center=true);
  }
  translate([-34.5, 51.0954988232819, 0]) {
    cube(size=[16, 4, 6], center=true);
  }
  translate([-34.5, -51.0954988232819, 0]) {
    cube(size=[16, 4, 6], center=true);
  }
}
