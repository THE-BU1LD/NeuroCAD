// ========================================
// a 11 x 18 x 0.2 cm plate with five 0.6 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[110, 180, 2], center=true);
  translate([44, 0, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([13.5967477524977, 75.1334647873171, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([-35.5967477524977, 46.4350349311054, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([-35.5967477524977, -46.4350349311054, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([13.5967477524977, -75.1334647873171, 0]) {
    cylinder(r=3, h=4, center=true);
  }
}
