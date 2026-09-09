// ========================================
// a 160 x 80 x 60 mm enclosure with 1 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 80, 60], center=true);
  translate([0, 0, 0.6]) {
    cube(size=[158, 78, 59.2], center=true);
  }
}
