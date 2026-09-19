// ========================================
// a 200 x 90 x 95 mm enclosure with 3 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[200, 90, 95], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[194, 84, 92.2], center=true);
  }
}
