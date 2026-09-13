// ========================================
// a 130 x 150 x 90 mm enclosure with 2 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[130, 150, 90], center=true);
  translate([0, 0, 1.1]) {
    cube(size=[126, 146, 88.2], center=true);
  }
}
