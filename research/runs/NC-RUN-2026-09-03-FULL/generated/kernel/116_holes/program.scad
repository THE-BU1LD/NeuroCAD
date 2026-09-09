// ========================================
// a 100 x 140 x 4 mm plate with five 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[100, 140, 4], center=true);
  translate([-40, -60, 0]) {
    cylinder(r=1.5, h=6, center=true);
  }
  translate([0, -60, 0]) {
    cylinder(r=1.5, h=6, center=true);
  }
  translate([40, -60, 0]) {
    cylinder(r=1.5, h=6, center=true);
  }
  translate([-40, 60, 0]) {
    cylinder(r=1.5, h=6, center=true);
  }
  translate([0, 60, 0]) {
    cylinder(r=1.5, h=6, center=true);
  }
}
