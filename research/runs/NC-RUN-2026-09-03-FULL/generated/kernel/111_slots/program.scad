// ========================================
// a 190 x 110 x 3 mm plate with three 12 x 3 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 110, 3], center=true);
  translate([-83, -43, 0]) {
    cube(size=[12, 3, 5], center=true);
  }
  translate([83, -43, 0]) {
    cube(size=[12, 3, 5], center=true);
  }
  translate([0, 43, 0]) {
    cube(size=[12, 3, 5], center=true);
  }
}
