// ========================================
// a 15 x 11 x 0.3 cm plate with one 0.8 x 0.4 cm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 110, 3], center=true);
  cube(size=[8, 4, 5], center=true);
}
