// ========================================
// a 15 x 6 x 6.5 cm enclosure with 0.3 cm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 60, 65], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[144, 54, 62.2], center=true);
  }
}
