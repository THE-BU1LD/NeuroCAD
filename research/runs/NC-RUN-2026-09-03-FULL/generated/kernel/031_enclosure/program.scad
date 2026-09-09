// ========================================
// a 180 x 80 x 70 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[180, 80, 70], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[174, 74, 67.2], center=true);
  }
}
