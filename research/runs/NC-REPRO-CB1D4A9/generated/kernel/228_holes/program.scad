// ========================================
// a 160 x 50 x 3 mm plate with four 6 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 50, 3], center=true);
  translate([-74, -19, 0]) {
    cylinder(r=3, h=5, center=true);
  }
  translate([-74, 19, 0]) {
    cylinder(r=3, h=5, center=true);
  }
  translate([74, -19, 0]) {
    cylinder(r=3, h=5, center=true);
  }
  translate([74, 19, 0]) {
    cylinder(r=3, h=5, center=true);
  }
}
