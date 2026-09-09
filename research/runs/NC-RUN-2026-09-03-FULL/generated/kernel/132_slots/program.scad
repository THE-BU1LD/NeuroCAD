// ========================================
// a 18 x 7 x 0.5 cm plate with four 2 x 0.3 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[180, 70, 5], center=true);
  translate([-70, -15, 0]) {
    cube(size=[20, 3, 7], center=true);
  }
  translate([-70, 15, 0]) {
    cube(size=[20, 3, 7], center=true);
  }
  translate([70, -15, 0]) {
    cube(size=[20, 3, 7], center=true);
  }
  translate([70, 15, 0]) {
    cube(size=[20, 3, 7], center=true);
  }
}
