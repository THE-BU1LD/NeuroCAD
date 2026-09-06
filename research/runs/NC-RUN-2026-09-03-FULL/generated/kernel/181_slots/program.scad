// ========================================
// a 190 x 120 x 2 mm plate with four 16 x 4 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 120, 2], center=true);
  translate([-79, -44, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
  translate([-79, 44, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
  translate([79, -44, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
  translate([79, 44, 0]) {
    cube(size=[16, 4, 4], center=true);
  }
}
