// ========================================
// a 70 x 150 x 4 mm plate with five 4 mm holes
// NeuroCAD canonical IR; dimensions are millimetres
// ========================================
$fn = 48;

difference() {
  cube(size=[70, 150, 4], center=true);
  translate([28, 0, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([8.65247584249853, 64.6718431080704, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([-22.6524758424985, 39.9693971558882, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([-22.6524758424985, -39.9693971558882, 0]) {
    cylinder(r=2, h=6, center=true);
  }
  translate([8.65247584249852, -64.6718431080704, 0]) {
    cylinder(r=2, h=6, center=true);
  }
}
