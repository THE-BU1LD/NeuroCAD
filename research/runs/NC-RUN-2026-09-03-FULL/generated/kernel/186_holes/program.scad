// ========================================
// a 210 x 170 x 4 mm plate with three 2 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[210, 170, 4], center=true);
  translate([-88, -68, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([88, -68, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([0, 68, 0]) {
    cylinder(r=1, h=6, center=true);
  }
}
