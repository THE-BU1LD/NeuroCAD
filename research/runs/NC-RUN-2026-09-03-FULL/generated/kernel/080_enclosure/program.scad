// ========================================
// a 130 x 110 x 50 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[130, 110, 50], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[124, 104, 47.2], center=true);
  }
}
