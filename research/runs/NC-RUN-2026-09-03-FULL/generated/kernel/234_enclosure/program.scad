// ========================================
// a 60 x 160 x 90 mm enclosure with 2 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[60, 160, 90], center=true);
  translate([0, 0, 1.1]) {
    cube(size=[56, 156, 88.2], center=true);
  }
}
