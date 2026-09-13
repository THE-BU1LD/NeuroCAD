// ========================================
// a 9 x 15 x 0.5 cm plate with three 1.6 x 0.3 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 150, 5], center=true);
  translate([29, 0, 0]) {
    cube(size=[16, 3, 7], center=true);
  }
  translate([-14.5, 51.0954988232819, 0]) {
    cube(size=[16, 3, 7], center=true);
  }
  translate([-14.5, -51.0954988232819, 0]) {
    cube(size=[16, 3, 7], center=true);
  }
}
