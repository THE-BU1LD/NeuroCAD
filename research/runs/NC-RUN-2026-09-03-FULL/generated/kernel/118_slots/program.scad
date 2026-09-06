// ========================================
// a 80 x 130 x 3 mm plate with one 12 x 3 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[80, 130, 3], center=true);
  cube(size=[12, 3, 5], center=true);
}
