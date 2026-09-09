// ========================================
// a 210 x 60 x 3 mm plate with three 8 x 2 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[210, 60, 3], center=true);
  translate([-97, -22, 0]) {
    cube(size=[8, 2, 5], center=true);
  }
  translate([97, -22, 0]) {
    cube(size=[8, 2, 5], center=true);
  }
  translate([0, 22, 0]) {
    cube(size=[8, 2, 5], center=true);
  }
}
