// ========================================
// a 11 x 5 x 9 cm enclosure with 0.15 cm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 50, 90], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[107, 47, 88.7], center=true);
  }
}
