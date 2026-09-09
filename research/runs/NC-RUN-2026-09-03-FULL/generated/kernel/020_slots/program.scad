// ========================================
// a 90 x 110 x 3 mm plate with one 10 x 3 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 110, 3], center=true);
  cube(size=[10, 3, 5], center=true);
}
