// ========================================
// a 70 x 150 x 4 mm plate with five 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[70, 150, 4], center=true);
  translate([-28, -68, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([0, -68, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([28, -68, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([-28, 68, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([0, 68, 0]) {
    cylinder(r=2, h=6, center=true);
  }
}
