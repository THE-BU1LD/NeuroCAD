// ========================================
// a 140 x 90 x 40 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[140, 90, 40], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[134, 84, 37.2], center=true);
  }
}
