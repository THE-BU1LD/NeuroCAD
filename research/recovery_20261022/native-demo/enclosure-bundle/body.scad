// ========================================
// electronics enclosure — body
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 64;

difference() {
  cube(size=[80, 60, 30], center=true);
  translate([0, 0, 1.1]) {
    cube(size=[76, 56, 28.2], center=true);
  }
  translate([0, -29, 8]) {
    cube(size=[12, 4, 7], center=true);
  }
}
