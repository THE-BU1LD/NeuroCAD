// ========================================
// a 190 x 160 x 25 mm enclosure with 1.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[190, 160, 25], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[187, 157, 23.7], center=true);
  }
}
