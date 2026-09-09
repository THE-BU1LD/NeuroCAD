// ========================================
// a 110 x 60 x 3 mm plate with one 16 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 60, 3], center=true);
  cube(size=[16, 2, 5], center=true);
}
