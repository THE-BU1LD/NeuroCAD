// ========================================
// a 80 x 140 x 4 mm plate with two 12 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[80, 140, 4], center=true);
  translate([-28, 0, 0]) {
    cube(size=[12, 2, 6], center=true);
  }
  translate([28, 0, 0]) {
    cube(size=[12, 2, 6], center=true);
  }
}
