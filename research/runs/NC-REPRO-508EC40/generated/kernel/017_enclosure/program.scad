// ========================================
// a 70 x 140 x 100 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[70, 140, 100], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[64, 134, 97.2], center=true);
  }
}
