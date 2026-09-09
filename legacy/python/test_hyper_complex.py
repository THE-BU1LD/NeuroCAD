from cad_kernel_hyper import CADKernelHyper


def run_complex():

    print("\n=== HYPER COMPLEX TEST ===")

    k = CADKernelHyper(bounds=1.2)

    mesh = k.build("complex", depth=8)

    print("Base faces:", len(mesh["faces"]))

    mesh = k.amplify(mesh, levels=3)

    print("Amplified faces:", len(mesh["faces"]))

    k.export_scad(mesh, "hyper_complex.scad")

    print("\nSCAD exported: hyper_complex.scad")


if __name__ == "__main__":
    run_complex()