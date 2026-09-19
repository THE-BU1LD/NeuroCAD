// ========================================
// a 120 x 130 x 40 mm enclosure with 1.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[120, 130, 40], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[117, 127, 38.7], center=true);
  }
}
