// ========================================
// a 160 x 120 x 40 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 120, 40], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[154, 114, 37.2], center=true);
  }
}
