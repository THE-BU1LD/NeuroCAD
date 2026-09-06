// ========================================
// a 60 x 120 x 3 mm plate with four 5 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[60, 120, 3], center=true);
  translate([-24, -54, 0]) {
    cylinder(r=2.5, h=5, center=true);
  }
  translate([-24, 54, 0]) {
    cylinder(r=2.5, h=5, center=true);
  }
  translate([24, -54, 0]) {
    cylinder(r=2.5, h=5, center=true);
  }
  translate([24, 54, 0]) {
    cylinder(r=2.5, h=5, center=true);
  }
}
