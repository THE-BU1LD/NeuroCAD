// ========================================
// a 170 x 170 x 2 mm plate with five 2 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[170, 170, 2], center=true);
  translate([-68, -68, 0]) {
    cylinder(r=1, h=4, center=true);
  }
  translate([0, -68, 0]) {
    cylinder(r=1, h=4, center=true);
  }
  translate([68, -68, 0]) {
    cylinder(r=1, h=4, center=true);
  }
  translate([-68, 68, 0]) {
    cylinder(r=1, h=4, center=true);
  }
  translate([0, 68, 0]) {
    cylinder(r=1, h=4, center=true);
  }
}
