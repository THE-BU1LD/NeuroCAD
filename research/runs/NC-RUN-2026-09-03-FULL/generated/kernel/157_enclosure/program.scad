// ========================================
// a 100 x 100 x 90 mm enclosure with 2.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[100, 100, 90], center=true);
  translate([0, 0, 1.35]) {
    cube(size=[95, 95, 87.7], center=true);
  }
}
