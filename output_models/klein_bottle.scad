
// === Klein Bottle (Parametric Approximation) ===
$fn = 96;

module klein() {
    for (u = [0:10:360]) {
        for (v = [0:10:360]) {

            x = (2 + cos(v)) * cos(u);
            y = (2 + cos(v)) * sin(u);
            z = sin(v);

            translate([x, y, z])
                sphere(r = 0.08);
        }
    }
}

scale([0.4,0.4,0.4])
    klein();
