// ========================================
// electronics enclosure — lid
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 64;

union() {
  cube(size=[79.4, 59.4, 2.5], center=true);
  translate([0, 0, -2.25]) {
    cube(size=[75.4, 55.4, 2], center=true);
  }
}
