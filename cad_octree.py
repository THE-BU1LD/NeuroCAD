import numpy as np
import torch

class OctreeNode:
    def __init__(self, bounds, depth=0):
        self.bounds = bounds  # (min, max)
        self.children = []
        self.depth = depth
        self.is_leaf = True
        self.sign = None


class AdaptiveOctree:

    def __init__(self, sdf, max_depth=6, device="cpu"):
        self.sdf = sdf
        self.max_depth = max_depth
        self.device = device

    def evaluate_corner_signs(self, bounds):

        corners = []
        for x in [bounds[0][0], bounds[1][0]]:
            for y in [bounds[0][1], bounds[1][1]]:
                for z in [bounds[0][2], bounds[1][2]]:
                    corners.append([x,y,z])

        p = torch.tensor(corners, device=self.device, dtype=torch.float32)
        vals = self.sdf(p).detach().cpu().numpy()

        return np.sign(vals)

    def subdivide(self, node):

        if node.depth >= self.max_depth:
            return

        signs = self.evaluate_corner_signs(node.bounds)

        if np.all(signs > 0) or np.all(signs < 0):
            node.sign = signs[0]
            return

        node.is_leaf = False

        minb, maxb = node.bounds
        mid = (np.array(minb) + np.array(maxb)) / 2

        for dx in [0,1]:
            for dy in [0,1]:
                for dz in [0,1]:

                    new_min = [
                        minb[0] if dx==0 else mid[0],
                        minb[1] if dy==0 else mid[1],
                        minb[2] if dz==0 else mid[2],
                    ]

                    new_max = [
                        mid[0] if dx==0 else maxb[0],
                        mid[1] if dy==0 else maxb[1],
                        mid[2] if dz==0 else maxb[2],
                    ]

                    child = OctreeNode((new_min, new_max), node.depth+1)
                    self.subdivide(child)
                    node.children.append(child)

    def build(self, bounds):
        root = OctreeNode(bounds)
        self.subdivide(root)
        return root