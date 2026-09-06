import numpy as np


class AdaptiveOctreeSampler:
    """
    Surface-adaptive octree sampler for implicit fields.
    Focuses samples near zero-crossings for high detail.
    """

    def __init__(self, sdf, bounds=1.2, max_depth=8, threshold=0.02):
        self.sdf = sdf
        self.bounds = bounds
        self.max_depth = max_depth
        self.threshold = threshold

    def _cell_values(self, center, size):
        vals = []
        half = size * 0.5
        for dx in (-1, 1):
            for dy in (-1, 1):
                for dz in (-1, 1):
                    p = center + np.array([dx, dy, dz]) * half
                    vals.append(self.sdf(p))
        return np.array(vals)

    def _subdivide(self, center, size, depth, cells):
        vals = self._cell_values(center, size)

        if depth >= self.max_depth or (vals.max() - vals.min()) < self.threshold:
            cells.append((center, size))
            return

        child = size / 2
        offsets = (-0.25, 0.25)

        for dx in offsets:
            for dy in offsets:
                for dz in offsets:
                    c = center + size * np.array([dx, dy, dz])
                    self._subdivide(c, child, depth + 1, cells)

    def sample(self):
        cells = []
        self._subdivide(np.zeros(3), self.bounds, 0, cells)

        centers = np.array([c for c, _ in cells])
        sizes = np.array([s for _, s in cells])

        return centers, sizes