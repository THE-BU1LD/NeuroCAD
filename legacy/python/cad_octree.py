import torch


class OctreeNode:
    __slots__ = ("min", "max", "children", "depth", "is_leaf", "sign")

    def __init__(self, min_bound, max_bound, depth=0):
        self.min = torch.tensor(min_bound, dtype=torch.float32)
        self.max = torch.tensor(max_bound, dtype=torch.float32)
        self.children = []
        self.depth = depth
        self.is_leaf = True
        self.sign = None


class AdaptiveOctree:
    def __init__(self, sdf, max_depth=6, device="cpu"):
        self.sdf = sdf
        self.max_depth = max_depth
        self.device = device

    def _corner_points(self, node):
        minb, maxb = node.min, node.max

        return torch.stack([
            torch.tensor([x, y, z], device=self.device)
            for x in (minb[0], maxb[0])
            for y in (minb[1], maxb[1])
            for z in (minb[2], maxb[2])
        ])

    def _corner_signs(self, node):
        pts = self._corner_points(node)
        vals = self.sdf(pts)
        return torch.sign(vals)

    def subdivide(self, node: OctreeNode):
        # Stop condition
        if node.depth >= self.max_depth:
            return

        signs = self._corner_signs(node)

        # Fully inside or outside
        if torch.all(signs > 0) or torch.all(signs < 0):
            node.sign = signs[0].item()
            return

        node.is_leaf = False

        minb = node.min
        maxb = node.max
        mid = (minb + maxb) * 0.5

        # Generate children
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):

                    new_min = torch.tensor([
                        minb[0] if dx == 0 else mid[0],
                        minb[1] if dy == 0 else mid[1],
                        minb[2] if dz == 0 else mid[2],
                    ], device=self.device)

                    new_max = torch.tensor([
                        mid[0] if dx == 0 else maxb[0],
                        mid[1] if dy == 0 else maxb[1],
                        mid[2] if dz == 0 else maxb[2],
                    ], device=self.device)

                    child = OctreeNode(new_min, new_max, node.depth + 1)
                    self.subdivide(child)
                    node.children.append(child)

    def build(self, bounds):
        root = OctreeNode(bounds[0], bounds[1], depth=0)
        self.subdivide(root)
        return root