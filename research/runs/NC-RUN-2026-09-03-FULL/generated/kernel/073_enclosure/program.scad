// ========================================
// a 160 x 130 x 65 mm enclosure with 1.5 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[160, 130, 65], center=true);
  translate([0, 0, 0.85]) {
    cube(size=[157, 127, 63.7], center=true);
  }
}
