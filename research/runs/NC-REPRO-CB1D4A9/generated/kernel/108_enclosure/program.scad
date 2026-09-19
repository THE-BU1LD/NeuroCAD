// ========================================
// a 9 x 9 x 3 cm enclosure with 0.3 cm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 90, 30], center=true);
  translate([0, 0, 1.6]) {
    cube(size=[84, 84, 27.2], center=true);
  }
}
