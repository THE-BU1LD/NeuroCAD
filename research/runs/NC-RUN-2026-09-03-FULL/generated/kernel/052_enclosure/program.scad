// ========================================
// a 150 x 120 x 60 mm enclosure with 2.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[150, 120, 60], center=true);
  translate([0, 0, 1.35]) {
    cube(size=[145, 115, 57.7], center=true);
  }
}
