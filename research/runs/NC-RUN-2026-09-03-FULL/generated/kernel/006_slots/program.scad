// ========================================
// a 190 x 50 x 5 mm plate with four 16 x 5 mm slots
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 50, 5], center=true);
  translate([-79, -9, 0]) {
    cube(size=[16, 5, 7], center=true);
  }
  translate([-79, 9, 0]) {
    cube(size=[16, 5, 7], center=true);
  }
  translate([79, -9, 0]) {
    cube(size=[16, 5, 7], center=true);
  }
  translate([79, 9, 0]) {
    cube(size=[16, 5, 7], center=true);
  }
}
