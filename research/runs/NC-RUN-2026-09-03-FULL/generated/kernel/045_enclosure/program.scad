// ========================================
// a 80 x 90 x 65 mm enclosure with 2 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[80, 90, 65], center=true);
  translate([0, 0, 1.1]) {
    cube(size=[76, 86, 63.2], center=true);
  }
}
