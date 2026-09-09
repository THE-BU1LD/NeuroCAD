// ========================================
// a 160 x 50 x 65 mm enclosure with 2.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 50, 65], center=true);
  translate([0, 0, 1.35]) {
    cube(size=[155, 45, 62.7], center=true);
  }
}
