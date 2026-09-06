// ========================================
// a 230 x 100 x 5 mm plate with two 12 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[230, 100, 5], center=true);
  translate([-103, 0, 0]) {
    cube(size=[12, 5, 7], center=true);
  }
  translate([103, 0, 0]) {
    cube(size=[12, 5, 7], center=true);
  }
}
