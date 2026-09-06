// ========================================
// a 11 x 9 x 0.4 cm plate with one 0.8 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 90, 4], center=true);
  cylinder(r=4, h=6, center=true);
}
