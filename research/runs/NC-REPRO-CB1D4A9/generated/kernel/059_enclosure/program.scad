// ========================================
// a 19 x 11 x 8 cm enclosure with 0.15 cm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 110, 80], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[187, 107, 78.7], center=true);
  }
}
