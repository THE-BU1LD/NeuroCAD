class SCADExporter:
    def export(self, verts, faces, path="mesh.scad"):
        with open(path, "w") as f:
            f.write("polyhedron(points=[\n")
            for v in verts:
                f.write(f"[{v[0]},{v[1]},{v[2]}],\n")
            f.write("], faces=[\n")
            for tri in faces:
                f.write(f"[{tri[0]},{tri[1]},{tri[2]}],\n")
            f.write("]);\n")
        return path