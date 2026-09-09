// ========================================
// a 180 x 80 x 2 mm plate with two 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[180, 80, 2], center=true);
  translate([-82, 0, 0]) {
    cylinder(r=1.5, h=4, center=true);
  }
  translate([82, 0, 0]) {
    cylinder(r=1.5, h=4, center=true);
  }
}
