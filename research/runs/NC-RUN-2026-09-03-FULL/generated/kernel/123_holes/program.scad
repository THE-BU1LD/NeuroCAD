// ========================================
// a 90 x 100 x 4 mm plate with five 8 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 100, 4], center=true);
  translate([-36, -41, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([0, -41, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([36, -41, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([-36, 41, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([0, 41, 0]) {
    cylinder(r=4, h=6, center=true);
  }
}
