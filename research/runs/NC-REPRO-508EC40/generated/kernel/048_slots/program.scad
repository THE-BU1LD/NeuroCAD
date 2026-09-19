// ========================================
// a 200 x 70 x 4 mm plate with one 12 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[200, 70, 4], center=true);
  cube(size=[12, 4, 6], center=true);
}
