// ========================================
// a 90 x 170 x 3 mm plate with three 3 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 170, 3], center=true);
  translate([36, 0, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-18, 65.8179306876173, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
  translate([-18, -65.8179306876173, 0]) {
    cylinder(r=1.5, h=5, center=true);
  }
}
