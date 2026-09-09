// ========================================
// a 120 x 70 x 5 mm plate with four 8 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[120, 70, 5], center=true);
  translate([-52, -27, 0]) {
    cylinder(r=4, h=7, center=true);
  }
  translate([-52, 27, 0]) {
    cylinder(r=4, h=7, center=true);
  }
  translate([52, -27, 0]) {
    cylinder(r=4, h=7, center=true);
  }
  translate([52, 27, 0]) {
    cylinder(r=4, h=7, center=true);
  }
}
