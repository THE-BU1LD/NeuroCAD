// ========================================
// a 16 x 14 x 8 cm enclosure with 0.25 cm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 140, 80], center=true);
  translate([0, 0, 1.35]) {
    cube(size=[155, 135, 77.7], center=true);
  }
}
