import numpy as np
import torch
from device import device


# ============================================================
# OCTREE NODE
# ============================================================

class OctreeNode:
    __slots__ = (
        "center",
        "size",
        "depth",
        "value",
        "children",
        "is_leaf",
    )

    def __init__(self, center, size, depth):
        self.center = np.asarray(center, dtype=np.float32)
        self.size = float(size)
        self.depth = depth
        self.value = None
        self.children = None
        self.is_leaf = True


# ============================================================
# SPARSE OCTREE WITH DUAL CONTOURING
# ============================================================

class SparseOctree:

    def __init__(
        self,
        sdf_model,
        max_depth=8,
        iso=0.0,
        threshold=0.02,
        batch_size=16384,
        max_nodes=2_000_000
    ):
        self.sdf = sdf_model
        self.max_depth = max_depth
        self.iso = iso
        self.threshold = threshold
        self.batch_size = batch_size
        self.max_nodes = max_nodes

        self.nodes = []
        self.leaves = []
        self.node_count = 0

    # ============================================================
    # BATCH SDF EVALUATION (GPU SAFE)
    # ============================================================

    def eval_sdf(self, pts_np):
        pts = torch.from_numpy(pts_np).float().to(device)
        with torch.no_grad():
            v = self.sdf(pts).detach().cpu().numpy()
        return v

    # ============================================================
    # BUILD OCTREE (ITERATIVE, MEMORY SAFE)
    # ============================================================

    def build(self, bounds=2.0):
        root = OctreeNode(np.zeros(3), bounds, 0)
        stack = [root]

        while stack:
            if self.node_count >= self.max_nodes:
                break

            batch = stack[:self.batch_size]
            stack = stack[self.batch_size:]

            centers = np.array([n.center for n in batch], dtype=np.float32)
            values = self.eval_sdf(centers)

            for node, val in zip(batch, values):
                node.value = float(val)
                self.nodes.append(node)
                self.node_count += 1

                if self.should_subdivide(node):
                    node.is_leaf = False
                    node.children = self.make_children(node)
                    stack.extend(node.children)
                else:
                    self.leaves.append(node)

        return root

    def should_subdivide(self, node):
        if node.depth >= self.max_depth:
            return False
        if abs(node.value - self.iso) < self.threshold:
            return True
        return False

    def make_children(self, node):
        half = node.size / 2
        quarter = node.size / 4

        offsets = np.array([
            [-quarter,-quarter,-quarter],
            [-quarter,-quarter, quarter],
            [-quarter, quarter,-quarter],
            [-quarter, quarter, quarter],
            [ quarter,-quarter,-quarter],
            [ quarter,-quarter, quarter],
            [ quarter, quarter,-quarter],
            [ quarter, quarter, quarter],
        ], dtype=np.float32)

        return [
            OctreeNode(node.center + off, half, node.depth + 1)
            for off in offsets
        ]

    # ============================================================
    # CORNERS + GRADIENT
    # ============================================================

    def cube_corners(self, node):
        h = node.size / 2
        offsets = np.array([
            [-h,-h,-h],
            [-h,-h, h],
            [-h, h,-h],
            [-h, h, h],
            [ h,-h,-h],
            [ h,-h, h],
            [ h, h,-h],
            [ h, h, h],
        ], dtype=np.float32)
        return node.center + offsets

    def estimate_gradient(self, p, eps=1e-4):
        offsets = np.eye(3) * eps
        pts1 = p + offsets
        pts2 = p - offsets
        v1 = self.eval_sdf(pts1)
        v2 = self.eval_sdf(pts2)
        g = (v1 - v2) / (2 * eps)
        return g

    # ============================================================
    # QEF SOLVER (Dual Contouring)
    # ============================================================

    def solve_qef(self, points, normals):
        A = normals
        b = np.sum(normals * points, axis=1)

        try:
            x, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
            return x.astype(np.float32)
        except:
            return np.mean(points, axis=0).astype(np.float32)

    # ============================================================
    # DUAL CONTOUR VERTEX EXTRACTION
    # ============================================================

    def dual_contour_vertices(self):
        vertices = []
        node_vertex = {}

        for i, leaf in enumerate(self.leaves):

            corners = self.cube_corners(leaf)
            values = self.eval_sdf(corners)

            if np.min(values) > 0 or np.max(values) < 0:
                continue

            intersections = []
            normals = []

            edges = [
                (0,1),(1,3),(3,2),(2,0),
                (4,5),(5,7),(7,6),(6,4),
                (0,4),(1,5),(2,6),(3,7)
            ]

            for a,b in edges:
                va = values[a]
                vb = values[b]

                if (va < 0 and vb > 0) or (va > 0 and vb < 0):
                    t = va / (va - vb)
                    p = corners[a] + t * (corners[b] - corners[a])
                    intersections.append(p)

                    g = self.estimate_gradient(p.reshape(1,3))[0]
                    g /= (np.linalg.norm(g) + 1e-8)
                    normals.append(g)

            if len(intersections) < 3:
                continue

            p = self.solve_qef(
                np.array(intersections),
                np.array(normals)
            )

            node_vertex[i] = len(vertices)
            vertices.append(p)

        return np.array(vertices), node_vertex

    # ============================================================
    # FACE GENERATION
    # ============================================================

    def build_faces(self, node_vertex):
        faces = []

        leaf_map = {
            tuple(np.round(n.center, 6)): i
            for i,n in enumerate(self.leaves)
        }

        directions = [
            (1,0,0),
            (0,1,0),
            (0,0,1),
        ]

        for i, leaf in enumerate(self.leaves):
            if i not in node_vertex:
                continue

            for d in directions:
                neighbor_center = leaf.center + np.array(d) * leaf.size
                key = tuple(np.round(neighbor_center,6))

                if key in leaf_map:
                    j = leaf_map[key]
                    if j in node_vertex:
                        v0 = node_vertex[i]
                        v1 = node_vertex[j]
                        faces.append([v0,v1,v1])
        return np.array(faces, dtype=np.int32)

    # ============================================================
    # VERTEX WELDING
    # ============================================================

    def weld_vertices(self, vertices, faces, eps=1e-6):
        unique = {}
        new_vertices = []
        index_map = {}

        for i,v in enumerate(vertices):
            key = tuple(np.round(v/eps).astype(int))
            if key not in unique:
                unique[key] = len(new_vertices)
                new_vertices.append(v)
            index_map[i] = unique[key]

        new_faces = []
        for f in faces:
            new_faces.append([
                index_map[f[0]],
                index_map[f[1]],
                index_map[f[2]]
            ])

        return np.array(new_vertices), np.array(new_faces)

    # ============================================================
    # FULL MESH EXTRACTION
    # ============================================================

    def extract_mesh(self):
        vertices, node_vertex = self.dual_contour_vertices()
        faces = self.build_faces(node_vertex)

        if len(vertices) == 0:
            return np.zeros((0,3)), np.zeros((0,3),dtype=np.int32)

        vertices, faces = self.weld_vertices(vertices, faces)

        return vertices, faces

    # ============================================================
    # OBJ EXPORT
    # ============================================================

    def export_obj(self, path):
        verts, faces = self.extract_mesh()

        with open(path, "w") as f:
            for v in verts:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for face in faces:
                f.write(
                    f"f {face[0]+1} {face[1]+1} {face[2]+1}\n"
                )

    # ============================================================
    # MEMORY ESTIMATE
    # ============================================================

    def memory_usage_mb(self):
        approx_per_node = 96
        return (self.node_count * approx_per_node) / (1024**2)

    # ============================================================
    # CLEAR
    # ============================================================

    def clear(self):
        self.nodes.clear()
        self.leaves.clear()
        self.node_count = 0
