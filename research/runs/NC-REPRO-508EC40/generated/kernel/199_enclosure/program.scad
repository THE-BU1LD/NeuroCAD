// ========================================
// a 16 x 15 x 2.5 cm enclosure with 0.1 cm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 150, 25], center=true);
  translate([0, 0, 0.6]) {
    cube(size=[158, 148, 24.2], center=true);
  }
}
