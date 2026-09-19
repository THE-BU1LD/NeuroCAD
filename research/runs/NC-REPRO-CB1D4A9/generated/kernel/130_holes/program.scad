// ========================================
// a 140 x 100 x 3 mm plate with five 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[140, 100, 3], center=true);
  translate([60, 0, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([18.5410196624968, 38.0422606518061, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-48.5410196624968, 23.5114100916989, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-48.5410196624969, -23.5114100916989, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([18.5410196624968, -38.0422606518061, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
}
