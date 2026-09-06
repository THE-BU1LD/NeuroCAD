// ========================================
// a 120 x 120 x 65 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[120, 120, 65], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[114, 114, 62.2], center=true);
  }
}
