// ========================================
// a 150 x 170 x 2 mm plate with three 12 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 170, 2], center=true);
  translate([-63, -73, 0]) {
    cube(size=[12, 4, 4], center=true);
  }
  translate([63, -73, 0]) {
    cube(size=[12, 4, 4], center=true);
  }
  translate([0, 73, 0]) {
    cube(size=[12, 4, 4], center=true);
  }
}
