// ========================================
// a 90 x 140 x 2 mm plate with one 16 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 140, 2], center=true);
  cube(size=[16, 4, 4], center=true);
}
