// ========================================
// a 140 x 70 x 50 mm enclosure with 1.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[140, 70, 50], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[137, 67, 48.7], center=true);
  }
}
