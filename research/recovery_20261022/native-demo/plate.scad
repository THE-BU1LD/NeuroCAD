// ========================================
// a 120 x 80 x 4 mm plate with four 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 96;

difference() {
  cube(size=[120, 80, 4], center=true);
  translate([-52, -32, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([-52, 32, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([52, -32, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([52, 32, 0]) {
    cylinder(r=2, h=6, center=true);
  }
}
