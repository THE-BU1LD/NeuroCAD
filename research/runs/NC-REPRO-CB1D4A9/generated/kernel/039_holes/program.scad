// ========================================
// a 190 x 50 x 2 mm plate with one 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 50, 2], center=true);
  cylinder(r=2, h=4, center=true);
}
