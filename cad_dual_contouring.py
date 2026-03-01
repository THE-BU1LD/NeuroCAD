import numpy as np

def solve_qef(positions, normals):

    A = np.array(normals)
    b = np.sum(A * positions, axis=1)

    try:
        x, *_ = np.linalg.lstsq(A, b, rcond=None)
    except:
        x = np.mean(positions, axis=0)

    return x


class DualContouring:

    def __init__(self, sdf, gradient_fn):
        self.sdf = sdf
        self.gradient = gradient_fn

    def extract_vertex(self, bounds):

        minb, maxb = bounds
        corners = []

        for x in [minb[0], maxb[0]]:
            for y in [minb[1], maxb[1]]:
                for z in [minb[2], maxb[2]]:
                    corners.append(np.array([x,y,z]))

        positions = []
        normals = []

        for c in corners:
            val = self.sdf(c)
            if abs(val) < 0.05:
                positions.append(c)
                normals.append(self.gradient(c))

        if len(positions) < 3:
            return None

        return solve_qef(np.array(positions), np.array(normals))