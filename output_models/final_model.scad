
// === Auto-generated from NeuroCAD ===
$fn = 96;

difference() {

    union() {

        // Hollow sphere
        difference() {
            sphere(r = 1.0);
            sphere(r = 0.82);
        }

        // Torus 1
        rotate_extrude()
            translate([0.7, 0, 0])
                circle(r = 0.14);

        // Torus 2
        rotate_extrude()
            translate([0.5, 0, 0])
                circle(r = 0.10);
    }

    // Cylindrical cuts
    for (angle = [0:90:270]) {
        rotate([0, 0, angle])
            translate([0.5, 0, 0])
                cylinder(h = 2.0, r = 0.12, center = true);
    }
}
