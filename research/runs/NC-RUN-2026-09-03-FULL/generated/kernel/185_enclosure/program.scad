// ========================================
// a 130 x 50 x 75 mm enclosure with 1 mm wall thickness
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[130, 50, 75], center=true);
  translate([0, 0, 0.6]) {
    cube(size=[128, 48, 74.2], center=true);
  }
}
