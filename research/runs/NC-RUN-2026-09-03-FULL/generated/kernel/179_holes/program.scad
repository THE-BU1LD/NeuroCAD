// ========================================
// a 190 x 40 x 5 mm plate with one 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 40, 5], center=true);
  cylinder(r=2, h=7, center=true);
}
