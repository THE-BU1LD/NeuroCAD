// ========================================
// a 140 x 100 x 3 mm plate with five 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[140, 100, 3], center=true);
  translate([-60, -40, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([0, -40, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([60, -40, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-60, 40, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([0, 40, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
}
