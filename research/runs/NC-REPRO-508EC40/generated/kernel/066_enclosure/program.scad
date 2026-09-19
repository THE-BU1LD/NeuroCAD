// ========================================
// a 200 x 110 x 80 mm enclosure with 1.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[200, 110, 80], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[197, 107, 78.7], center=true);
  }
}
