// ========================================
// a 90 x 100 x 4 mm plate with five 8 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 100, 4], center=true);
  translate([36, 0, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([11.1246117974981, 38.9933171681013, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([-29.1246117974981, 24.0991953439914, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([-29.1246117974981, -24.0991953439914, 0]) {
    cylinder(r=4, h=6, center=true);
  }
  translate([11.1246117974981, -38.9933171681013, 0]) {
    cylinder(r=4, h=6, center=true);
  }
}
