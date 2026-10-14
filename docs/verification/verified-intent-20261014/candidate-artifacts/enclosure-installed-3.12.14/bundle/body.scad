// ========================================
// electronics enclosure — body
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 64;

difference() {
  cube(size=[80, 60, 30], center=true);
  translate([0, 0, 1.3]) {
    cube(size=[75.2, 55.2, 27.8], center=true);
  }
  translate([0, -28.8, 8]) {
    cube(size=[12, 4.4, 7], center=true);
  }
}
