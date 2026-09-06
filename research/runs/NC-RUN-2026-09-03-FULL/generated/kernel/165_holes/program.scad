// ========================================
// a 190 x 170 x 2 mm plate with one 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 170, 2], center=true);
  cylinder(r=1.5, h=4, center=true);
}
