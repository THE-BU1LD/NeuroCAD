// ========================================
// a 140 x 90 x 35 mm enclosure with 4 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[140, 90, 35], center=true);
  translate([0, 0, 2.1]) {
    cube(size=[132, 82, 31.2], center=true);
  }
}
