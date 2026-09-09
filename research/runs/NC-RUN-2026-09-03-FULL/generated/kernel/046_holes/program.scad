// ========================================
// a 180 x 100 x 5 mm plate with six 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[180, 100, 5], center=true);
  translate([-80, -40, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([0, -40, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([80, -40, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([-80, 40, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([0, 40, 0]) {
    cylinder(r=2, h=7, center=true);
  }
  translate([80, 40, 0]) {
    cylinder(r=2, h=7, center=true);
  }
}
