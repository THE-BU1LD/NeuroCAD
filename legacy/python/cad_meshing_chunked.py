import numpy as np


class ChunkedDualContouring:
    """
    Runs dual contouring in chunks to avoid memory blowups.
    """

    def __init__(self, dc, chunk=64):
        self.dc = dc
        self.chunk = chunk

    def extract(self, phi, spacing, origin):
        verts_all = []
        faces_all = []
        offset = 0

        n = phi.shape[0]

        for x in range(0, n, self.chunk):
            xs = slice(x, min(x + self.chunk, n))
            phi_block = phi[xs, :, :]

            verts, faces, _ = self.dc.extract(phi_block, spacing, origin)

            faces = faces + offset

            verts_all.append(verts)
            faces_all.append(faces)

            offset += len(verts)

        return np.vstack(verts_all), np.vstack(faces_all)