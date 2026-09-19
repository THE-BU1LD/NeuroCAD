// ========================================
// a 150 x 90 x 70 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 90, 70], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[144, 84, 67.2], center=true);
  }
}
