// ========================================
// a 220 x 90 x 3 mm plate with three 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[220, 90, 3], center=true);
  translate([101, 0, 0]) {
    cylinder(r=2, h=5, center=true);
  }
  translate([-50.5, 31.1769145362398, 0]) {
    cylinder(r=2, h=5, center=true);
  }
  translate([-50.5, -31.1769145362398, 0]) {
    cylinder(r=2, h=5, center=true);
  }
}
