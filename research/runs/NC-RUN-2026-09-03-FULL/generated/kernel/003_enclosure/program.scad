// ========================================
// a 190 x 90 x 50 mm enclosure with 2.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 90, 50], center=true);
  translate([0, 0, 1.35]) {
    cube(size=[185, 85, 47.7], center=true);
  }
}
