import numpy as np


class TopologyAmplifier:
    """
    Fast mesh amplification via recursive subdivision.
    """

    @staticmethod
    def subdivide(verts, faces, levels=1):
        for _ in range(levels):
            verts, faces = TopologyAmplifier._subdivide_once(verts, faces)
        return verts, faces

    @staticmethod
    def _subdivide_once(verts, faces):
        verts = verts.tolist()
        new_faces = []

        for f in faces:
            a, b, c = f
            va, vb, vc = verts[a], verts[b], verts[c]

            ab = [(va[i] + vb[i]) / 2 for i in range(3)]
            bc = [(vb[i] + vc[i]) / 2 for i in range(3)]
            ca = [(vc[i] + va[i]) / 2 for i in range(3)]

            iab = len(verts); verts.append(ab)
            ibc = len(verts); verts.append(bc)
            ica = len(verts); verts.append(ca)

            new_faces += [
                [a, iab, ica],
                [iab, b, ibc],
                [ica, ibc, c],
                [iab, ibc, ica],
            ]

        return np.array(verts), np.array(new_faces)