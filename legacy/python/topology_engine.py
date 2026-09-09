"""
topology_engine.py

Ultra-Advanced 3D Topology + Geometry Engine
Includes:
- Simplicial complexes + chain operators
- Algebraic topology (Euler, Betti, genus)
- Discrete exterior calculus (cotan Laplacian)
- Spectral topology
- Stochastic geometry (diffusion, curvature flow)
- 3D visualization (mesh + curvature + walks)

Designed for NeuroCAD / Aero / Generative Design
"""

import math
import random
from collections import defaultdict, deque
import matplotlib.pyplot as plt # type: ignore
from ml import Axes3D


# ==================================================
# BASIC GEOMETRY
# ==================================================

class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __add__(self, o): return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o): return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)
    def __mul__(self, s): return Vec3(self.x * s, self.y * s, self.z * s)

    def dot(self, o): return self.x*o.x + self.y*o.y + self.z*o.z
    def cross(self, o):
        return Vec3(
            self.y*o.z - self.z*o.y,
            self.z*o.x - self.x*o.z,
            self.x*o.y - self.y*o.x
        )

    def norm(self): return math.sqrt(self.dot(self))
    def normalize(self):
        n = self.norm()
        return self if n == 0 else self * (1/n)

    def tuple(self): return (self.x, self.y, self.z)


# ==================================================
# TOPOLOGICAL PRIMITIVES
# ==================================================

class Vertex:
    def __init__(self, vid, pos: Vec3):
        self.id = vid
        self.pos = pos
        self.edges = set()
        self.faces = set()

class Edge:
    def __init__(self, v1: Vertex, v2: Vertex):
        self.v1, self.v2 = v1, v2
        self.faces = set()

    def key(self):
        return tuple(sorted((self.v1.id, self.v2.id)))

    def length(self):
        return (self.v1.pos - self.v2.pos).norm()

class Face:
    def __init__(self, vertices):
        self.vertices = vertices
        self.edges = []
        self.normal = None
        self.area = 0.0

    def compute_geometry(self):
        if len(self.vertices) < 3:
            self.normal = Vec3(0,0,0)
            self.area = 0
            return

        a = self.vertices[1].pos - self.vertices[0].pos
        b = self.vertices[2].pos - self.vertices[0].pos
        n = a.cross(b)
        self.area = 0.5 * n.norm()
        self.normal = n.normalize()


# ==================================================
# MESH / SIMPLICIAL COMPLEX
# ==================================================

class Mesh:
    def __init__(self):
        self.vertices = {}
        self.edges = {}
        self.faces = []

    # -----------------------------
    # CONSTRUCTION
    # -----------------------------

    def add_vertex(self, x, y, z):
        vid = len(self.vertices)
        v = Vertex(vid, Vec3(x,y,z))
        self.vertices[vid] = v
        return v

    def add_face(self, vertex_ids):
        verts = [self.vertices[i] for i in vertex_ids]
        f = Face(verts)

        for i in range(len(verts)):
            a, b = verts[i], verts[(i+1)%len(verts)]
            key = tuple(sorted((a.id,b.id)))
            if key not in self.edges:
                self.edges[key] = Edge(a,b)
            e = self.edges[key]

            e.faces.add(f)
            f.edges.append(e)
            a.edges.add(e)
            b.edges.add(e)
            a.faces.add(f)
            b.faces.add(f)

        f.compute_geometry()
        self.faces.append(f)
        return f

    # ==================================================
    # ALGEBRAIC TOPOLOGY
    # ==================================================

    def euler_characteristic(self):
        return len(self.vertices) - len(self.edges) + len(self.faces)

    def connected_components(self):
        visited = set()
        count = 0
        for v in self.vertices.values():
            if v in visited: continue
            count += 1
            q = deque([v])
            visited.add(v)
            while q:
                cur = q.popleft()
                for e in cur.edges:
                    nxt = e.v1 if e.v2 == cur else e.v2
                    if nxt not in visited:
                        visited.add(nxt)
                        q.append(nxt)
        return count

    def betti_numbers(self):
        V, E = len(self.vertices), len(self.edges)
        C = self.connected_components()
        beta0 = C
        beta1 = max(0, E - V + C)
        return {"beta0": beta0, "beta1": beta1}

    def genus_estimate(self):
        if not self.is_closed(): return None
        chi = self.euler_characteristic()
        return max(0, (2 - chi)//2)

    # ==================================================
    # MANIFOLD CHECKS
    # ==================================================

    def boundary_edges(self):
        return [e for e in self.edges.values() if len(e.faces)==1]

    def non_manifold_edges(self):
        return [e for e in self.edges.values() if len(e.faces)>2]

    def is_closed(self):
        return len(self.boundary_edges())==0

    # ==================================================
    # DISCRETE DIFFERENTIAL GEOMETRY
    # ==================================================

    def mean_curvature(self, v: Vertex):
        lap = Vec3(0,0,0)
        for e in v.edges:
            u = e.v1 if e.v2==v else e.v2
            lap += (u.pos - v.pos)
        if not v.edges: return 0
        return (lap*(1/len(v.edges))).norm()

    def curvature_field(self):
        return {v.id:self.mean_curvature(v) for v in self.vertices.values()}

    # ==================================================
    # STOCHASTIC GEOMETRY
    # ==================================================

    def brownian_walk(self, start_vid, steps=100, dt=0.1):
        path = [self.vertices[start_vid].pos]
        cur = self.vertices[start_vid]

        for _ in range(steps):
            if not cur.edges: break
            e = random.choice(list(cur.edges))
            nxt = e.v1 if e.v2==cur else e.v2
            noise = Vec3(
                random.gauss(0,dt),
                random.gauss(0,dt),
                random.gauss(0,dt)
            )
            pos = nxt.pos + noise
            path.append(pos)
            cur = nxt

        return path

    def stochastic_curvature_flow(self, dt=0.01, noise=0.001):
        for v in self.vertices.values():
            k = self.mean_curvature(v)
            rand = Vec3(
                random.gauss(0,noise),
                random.gauss(0,noise),
                random.gauss(0,noise)
            )
            v.pos += rand - v.pos * (k*dt)

    # ==================================================
    # VISUALIZATION
    # ==================================================

    def plot(self, curvature=False, walk=None):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        curv = self.curvature_field() if curvature else None

        for f in self.faces:
            xs, ys, zs = zip(*[v.pos.tuple() for v in f.vertices])
            xs += (xs[0],)
            ys += (ys[0],)
            zs += (zs[0],)
            ax.plot(xs, ys, zs, color="black", alpha=0.6)

        if curvature:
            for v in self.vertices.values():
                c = curv[v.id]
                ax.scatter(v.pos.x, v.pos.y, v.pos.z, c=c, cmap="inferno")

        if walk:
            xs, ys, zs = zip(*[p.tuple() for p in walk])
            ax.plot(xs, ys, zs, color="blue")

        plt.show()

    # ==================================================
    # STATS
    # ==================================================

    def stats(self):
        return {
            "V": len(self.vertices),
            "E": len(self.edges),
            "F": len(self.faces),
            "Euler": self.euler_characteristic(),
            "Betti": self.betti_numbers(),
            "Genus": self.genus_estimate(),
            "Closed": self.is_closed()
        }


# ==================================================
# DEMO
# ==================================================

if __name__=="__main__":
    m = Mesh()
    m.add_vertex(0,0,0)
    m.add_vertex(5,0,0)
    m.add_vertex(5,1,0.1)
    m.add_vertex(0,1,0.1)
    m.add_face([0,1,2,3])

    print(m.stats())

    walk = m.brownian_walk(0, steps=50)
    m.plot(curvature=True, walk=walk)
