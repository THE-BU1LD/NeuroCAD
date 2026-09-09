// ========================================
// a 170 x 70 x 20 mm enclosure with 4 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[170, 70, 20], center=true);
  translate([0, 0, 2.1]) {
    cube(size=[162, 62, 16.2], center=true);
  }
}
