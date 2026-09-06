// ========================================
// a 160 x 100 x 4 mm plate with six 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 100, 4], center=true);
  translate([-70, -40, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([0, -40, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([70, -40, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([-70, 40, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([0, 40, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([70, 40, 0]) {
    cylinder(r=2, h=6, center=true);
  }
}
