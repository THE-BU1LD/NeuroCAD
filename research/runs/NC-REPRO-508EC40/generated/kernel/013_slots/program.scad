// ========================================
// a 15 x 10 x 0.5 cm plate with three 1 x 0.4 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 100, 5], center=true);
  translate([65, 0, 0]) {
    cube(size=[10, 4, 7], center=true);
  }
  translate([-32.5, 34.6410161513775, 0]) {
    cube(size=[10, 4, 7], center=true);
  }
  translate([-32.5, -34.6410161513775, 0]) {
    cube(size=[10, 4, 7], center=true);
  }
}
