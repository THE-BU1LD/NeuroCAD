// ========================================
// a 190 x 110 x 35 mm enclosure with 2 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 110, 35], center=true);
  translate([0, 0, 1.1]) {
    cube(size=[186, 106, 33.2], center=true);
  }
}
