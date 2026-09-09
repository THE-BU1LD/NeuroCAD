// ========================================
// a 110 x 170 x 2 mm plate with three 2 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 170, 2], center=true);
  translate([-44, -74, 0]) {
    cylinder(r=1, h=4, center=true);
  }
  translate([44, -74, 0]) {
    cylinder(r=1, h=4, center=true);
  }
  translate([0, 74, 0]) {
    cylinder(r=1, h=4, center=true);
  }
}
