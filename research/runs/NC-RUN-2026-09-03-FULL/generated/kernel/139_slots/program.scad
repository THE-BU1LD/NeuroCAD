// ========================================
// a 90 x 180 x 2 mm plate with one 10 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 180, 2], center=true);
  cube(size=[10, 4, 4], center=true);
}
