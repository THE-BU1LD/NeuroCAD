// ========================================
// a 9 x 6 x 0.4 cm plate with five 0.2 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[90, 60, 4], center=true);
  translate([39, 0, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([12.051662780623, 22.8253563910837, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([-31.5516627806229, 14.1068460550194, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([-31.551662780623, -14.1068460550194, 0]) {
    cylinder(r=1, h=6, center=true);
  }
  translate([12.0516627806229, -22.8253563910837, 0]) {
    cylinder(r=1, h=6, center=true);
  }
}
