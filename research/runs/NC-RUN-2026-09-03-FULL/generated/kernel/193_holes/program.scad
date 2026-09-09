// ========================================
// a 220 x 90 x 3 mm plate with three 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[220, 90, 3], center=true);
  translate([-101, -36, 0]) {
    cylinder(r=2, h=5, center=true);
  }
  translate([101, -36, 0]) {
    cylinder(r=2, h=5, center=true);
  }
  translate([0, 36, 0]) {
    cylinder(r=2, h=5, center=true);
  }
}
