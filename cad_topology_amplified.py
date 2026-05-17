import numpy as np


class TopologyAmplifier:
    """
    Efficient mesh subdivision using midpoint caching.
    Prevents duplicate vertices on shared edges.
    """

    @staticmethod
    def subdivide(verts, faces, levels=1):
        verts = np.asarray(verts, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int32)

        for _ in range(levels):
            verts, faces = TopologyAmplifier._subdivide_once(verts, faces)

        return verts, faces

    @staticmethod
    def _subdivide_once(verts, faces):
        verts_list = verts.tolist()
        midpoint_cache = {}  # (min_idx, max_idx) -> new_vertex_index
        new_faces = []

        def get_midpoint(i, j):
            key = tuple(sorted((i, j)))
            if key in midpoint_cache:
                return midpoint_cache[key]

            vi, vj = verts_list[i], verts_list[j]
            midpoint = [(vi[k] + vj[k]) * 0.5 for k in range(3)]

            idx = len(verts_list)
            verts_list.append(midpoint)
            midpoint_cache[key] = idx
            return idx

        for a, b, c in faces:
            ab = get_midpoint(a, b)
            bc = get_midpoint(b, c)
            ca = get_midpoint(c, a)

            new_faces.extend([
                [a, ab, ca],
                [ab, b, bc],
                [ca, bc, c],
                [ab, bc, ca],
            ])

        return np.array(verts_list, dtype=np.float64), np.array(new_faces, dtype=np.int32)