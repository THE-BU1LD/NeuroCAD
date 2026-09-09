// ========================================
// a 170 x 170 x 2 mm plate with one 20 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[170, 170, 2], center=true);
  cube(size=[20, 2, 4], center=true);
}
