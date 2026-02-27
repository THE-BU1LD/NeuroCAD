import numpy as np


class QuadTopology:

    @staticmethod
    def faces_to_edges(faces):
        edges = set()
        for f in faces:
            edges.add(tuple(sorted((f[0], f[1]))))
            edges.add(tuple(sorted((f[1], f[2]))))
            edges.add(tuple(sorted((f[2], f[0]))))
        return list(edges)

    @staticmethod
    def count_edges(faces):
        return len(QuadTopology.faces_to_edges(faces))

    @staticmethod
    def subdivide(verts, faces):
        """
        Simple quad-like subdivision via face splitting.
        Explodes topology density.
        """

        new_verts = verts.tolist()
        new_faces = []

        for f in faces:
            v0, v1, v2 = f
            c = (verts[v0] + verts[v1] + verts[v2]) / 3.0
            ci = len(new_verts)
            new_verts.append(c)

            new_faces.append([v0, v1, ci])
            new_faces.append([v1, v2, ci])
            new_faces.append([v2, v0, ci])

        return np.array(new_verts), np.array(new_faces)
