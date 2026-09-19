// ========================================
// a 70 x 160 x 60 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[70, 160, 60], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[64, 154, 57.2], center=true);
  }
}
