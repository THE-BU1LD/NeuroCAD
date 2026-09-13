// ========================================
// a 24 x 16 x 0.2 cm plate with five 0.6 cm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[240, 160, 2], center=true);
  translate([104, 0, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([32.1377674149945, 60.8676170428898, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([-84.1377674149945, 37.6182561467183, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([-84.1377674149945, -37.6182561467183, 0]) {
    cylinder(r=3, h=4, center=true);
  }
  translate([32.1377674149945, -60.8676170428898, 0]) {
    cylinder(r=3, h=4, center=true);
  }
}
