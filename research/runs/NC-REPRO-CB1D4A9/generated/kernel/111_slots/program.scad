// ========================================
// a 190 x 110 x 3 mm plate with three 12 x 3 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 110, 3], center=true);
  translate([83, 0, 0]) {
    cube(size=[12, 3, 5], center=true);
  }
  translate([-41.5, 37.2390923627309, 0]) {
    cube(size=[12, 3, 5], center=true);
  }
  translate([-41.5, -37.2390923627309, 0]) {
    cube(size=[12, 3, 5], center=true);
  }
}
