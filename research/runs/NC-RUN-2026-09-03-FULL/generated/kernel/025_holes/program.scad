// ========================================
// a 150 x 110 x 3 mm plate with four 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 110, 3], center=true);
  translate([-64, -44, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-64, 44, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([64, -44, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([64, 44, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
}
