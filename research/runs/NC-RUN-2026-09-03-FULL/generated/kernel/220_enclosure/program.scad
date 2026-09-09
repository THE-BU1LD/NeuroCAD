// ========================================
// a 100 x 90 x 95 mm enclosure with 4 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[100, 90, 95], center=true);
  translate([0, 0, 2.1]) {
    cube(size=[92, 82, 91.2], center=true);
  }
}
