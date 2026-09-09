import math
import time
import hashlib
import numpy as np
import torch
import threading
import uuid
import trimesh

from cad_sdf import SDFPrimitives

from surfaces import rotation_matrix

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.float32


class KernelVersion:

    major = 2
    minor = 0
    patch = 0

    @classmethod
    def string(cls):
        return f"{cls.major}.{cls.minor}.{cls.patch}"


class KernelConfig:

    def __init__(self):

        self.device = DEVICE
        self.dtype = DTYPE
        self.seed = 1337
        self.precision = 1e-8
        self.max_threads = 8
        self.memory_limit = 8_000_000_000

        torch.manual_seed(self.seed)
        np.random.seed(self.seed)


class TensorBackend:

    def __init__(self, config: KernelConfig):

        self.device = config.device
        self.dtype = config.dtype

    def tensor(self, data):

        return torch.tensor(data, device=self.device, dtype=self.dtype)

    def zeros(self, shape):

        return torch.zeros(shape, device=self.device, dtype=self.dtype)

    def ones(self, shape):

        return torch.ones(shape, device=self.device, dtype=self.dtype)

    def rand(self, shape):

        return torch.rand(shape, device=self.device, dtype=self.dtype)

    def linspace(self, a, b, n):

        return torch.linspace(a, b, n, device=self.device, dtype=self.dtype)

    def stack(self, tensors, dim=0):

        return torch.stack(tensors, dim=dim)

    def cat(self, tensors, dim=0):

        return torch.cat(tensors, dim=dim)


class VectorOps:

    def norm(self, v):

        return torch.linalg.norm(v, dim=-1)

    def normalize(self, v):

        n = torch.linalg.norm(v, dim=-1, keepdim=True)
        n = torch.clamp(n, min=1e-12)
        return v / n

    def dot(self, a, b):

        return torch.sum(a * b, dim=-1)

    def cross(self, a, b):

        return torch.cross(a, b)

    def distance(self, a, b):

        return torch.linalg.norm(a - b, dim=-1)

    def reflect(self, v, n):

        return v - 2 * self.dot(v, n).unsqueeze(-1) * n

    def project(self, a, b):

        d = self.dot(a, b) / torch.clamp(self.dot(b, b), min=1e-12)
        return d.unsqueeze(-1) * b


class MatrixOps:

    def identity(self):

        return torch.eye(4, device=DEVICE, dtype=DTYPE)

    def translate(self, x, y, z):

        m = torch.eye(4, device=DEVICE, dtype=DTYPE)
        m[0, 3] = x
        m[1, 3] = y
        m[2, 3] = z
        return m

    def scale(self, x, y, z):

        m = torch.eye(4, device=DEVICE, dtype=DTYPE)
        m[0, 0] = x
        m[1, 1] = y
        m[2, 2] = z
        return m

    def rotate_x(self, a):

        c = math.cos(a)
        s = math.sin(a)

        m = torch.eye(4, device=DEVICE, dtype=DTYPE)

        m[1, 1] = c
        m[1, 2] = -s
        m[2, 1] = s
        m[2, 2] = c

        return m

    def rotate_y(self, a):

        c = math.cos(a)
        s = math.sin(a)

        m = torch.eye(4, device=DEVICE, dtype=DTYPE)

        m[0, 0] = c
        m[0, 2] = s
        m[2, 0] = -s
        m[2, 2] = c

        return m

    def rotate_z(self, a):

        c = math.cos(a)
        s = math.sin(a)

        m = torch.eye(4, device=DEVICE, dtype=DTYPE)

        m[0, 0] = c
        m[0, 1] = -s
        m[1, 0] = s
        m[1, 1] = c

        return m

    def multiply(self, a, b):

        return a @ b


class Transform:

    def __init__(self):

        self.matrix = torch.eye(4, device=DEVICE, dtype=DTYPE)

    def apply(self, pts):

        ones = torch.ones((pts.shape[0], 1), device=pts.device)
        ph = torch.cat([pts, ones], dim=1)
        pt = (self.matrix @ ph.T).T
        return pt[:, :3]

    def translate(self, x, y, z):

        m = MatrixOps().translate(x, y, z)
        self.matrix = m @ self.matrix

    def scale(self, x, y, z):

        m = MatrixOps().scale(x, y, z)
        self.matrix = m @ self.matrix

    def rotate_x(self, a):

        m = MatrixOps().rotate_x(a)
        self.matrix = m @ self.matrix

    def rotate_y(self, a):

        m = MatrixOps().rotate_y(a)
        self.matrix = m @ self.matrix

    def rotate_z(self, a):

        m = MatrixOps().rotate_z(a)
        self.matrix = m @ self.matrix


class SpatialHash:

    def __init__(self, cell=0.1):

        self.cell = cell
        self.table = {}

    def key(self, p):

        return tuple((p / self.cell).astype(int))

    def insert(self, p, value):

        k = self.key(p)
        if k not in self.table:
            self.table[k] = []
        self.table[k].append(value)

    def query(self, p):

        k = self.key(p)
        return self.table.get(k, [])


class KernelTimer:

    def __init__(self):

        self.t0 = None

    def start(self):

        self.t0 = time.time()

    def stop(self):

        return time.time() - self.t0


class MemoryPool:

    def __init__(self):

        self.pool = []

    def allocate(self, shape):

        if self.pool:
            t = self.pool.pop()
            if t.shape == shape:
                return t
        return torch.zeros(shape, device=DEVICE)

    def release(self, t):

        self.pool.append(t)


class KernelRegistry:

    def __init__(self):

        self.objects = {}

    def register(self, name, obj):

        self.objects[name] = obj

    def get(self, name):

        return self.objects.get(name)


class HashUtils:

    def hash_string(self, s):

        return hashlib.md5(s.encode()).hexdigest()

    def hash_array(self, arr):

        return hashlib.md5(arr.tobytes()).hexdigest()

    def hash_tensor(self, t):

        return hashlib.md5(t.cpu().numpy().tobytes()).hexdigest()


class GeometryBuffer:

    def __init__(self):

        self.verts = []
        self.faces = []

    def add_mesh(self, verts, faces):

        offset = len(self.verts)

        self.verts.extend(verts)

        self.faces.extend(f + offset for f in faces)

    def build(self):

        return {
            "verts": np.array(self.verts),
            "faces": np.array(self.faces)
        }


class KernelState:

    def __init__(self):

        self.id = str(uuid.uuid4())
        self.created = time.time()
        self.metadata = {}


class KernelBase:

    def __init__(self):

        self.config = KernelConfig()

        self.backend = TensorBackend(self.config)

        self.vops = VectorOps()

        self.mops = MatrixOps()

        self.registry = KernelRegistry()

        self.memory = MemoryPool()

        self.state = KernelState()

    def tensor(self, data):

        return self.backend.tensor(data)

    def zeros(self, shape):

        return self.backend.zeros(shape)

    def ones(self, shape):

        return self.backend.ones(shape)

    def rand(self, shape):

        return self.backend.rand(shape)


class ThreadPool:

    def __init__(self, workers=4):

        self.workers = workers
        self.tasks = []
        self.lock = threading.Lock()

    def submit(self, fn, *args):

        t = threading.Thread(target=fn, args=args)
        self.tasks.append(t)
        t.start()

    def wait(self):

        for t in self.tasks:
            t.join()

        self.tasks = []


class GeometryStats:

    def compute(self, mesh):

        v = mesh["verts"]
        f = mesh["faces"]

        bbox_min = np.min(v, axis=0)
        bbox_max = np.max(v, axis=0)

        center = np.mean(v, axis=0)

        return {
            "verts": len(v),
            "faces": len(f),
            "bbox_min": bbox_min,
            "bbox_max": bbox_max,
            "center": center
        }


class KernelCore(KernelBase):

    def __init__(self):

        super().__init__()

        self.stats = GeometryStats()

        self.hash = HashUtils()

        self.timer = KernelTimer()

        self.threads = ThreadPool(self.config.max_threads)

    def analyze(self, mesh):

        return self.stats.compute(mesh)
import torch
import numpy as np
import math


class EigenSolver:

    def eigen(self, M):

        vals, vecs = torch.linalg.eig(M)
        vals = torch.real(vals)
        vecs = torch.real(vecs)

        return vals, vecs


    def symmetric(self, M):

        vals, vecs = torch.linalg.eigh(M)

        return vals, vecs


    def largest(self, M):

        vals, vecs = torch.linalg.eigh(M)

        idx = torch.argmax(vals)

        return vals[idx], vecs[:, idx]


class SVD:

    def decompose(self, M):

        U, S, V = torch.linalg.svd(M)

        return U, S, V


    def reconstruct(self, U, S, V):

        return U @ torch.diag(S) @ V


class Covariance:

    def matrix(self, pts):

        mean = torch.mean(pts, dim=0)

        centered = pts - mean

        cov = centered.T @ centered / (pts.shape[0] - 1)

        return cov


class PCA:

    def __init__(self):

        self.eig = EigenSolver()
        self.cov = Covariance()


    def fit(self, pts):

        C = self.cov.matrix(pts)

        vals, vecs = self.eig.symmetric(C)

        order = torch.argsort(vals, descending=True)

        vals = vals[order]
        vecs = vecs[:, order]

        return vals, vecs


    def project(self, pts, vecs):

        return pts @ vecs


class OrthonormalBasis:

    def build(self, n):

        n = n / torch.linalg.norm(n)

        if abs(n[0]) > abs(n[2]):
            a = torch.tensor([-n[1], n[0], 0.0], device=n.device)
        else:
            a = torch.tensor([0.0, -n[2], n[1]], device=n.device)

        a = a / torch.linalg.norm(a)

        b = torch.cross(n, a)

        return torch.stack([a, b, n])


class Quaternion:

    def from_axis_angle(self, axis, angle):

        axis = axis / torch.linalg.norm(axis)

        s = math.sin(angle / 2)

        return torch.tensor([
            axis[0] * s,
            axis[1] * s,
            axis[2] * s,
            math.cos(angle / 2)
        ])


    def multiply(self, q1, q2):

        x1,y1,z1,w1 = q1
        x2,y2,z2,w2 = q2

        return torch.tensor([
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2,
            w1*w2 - x1*x2 - y1*y2 - z1*z2
        ])


    def to_matrix(self, q):

        x,y,z,w = q

        return torch.tensor([
            [1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
            [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
            [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]
        ])


class RigidTransform:

    def __init__(self):

        self.R = torch.eye(3)
        self.t = torch.zeros(3)


    def apply(self, pts):

        return pts @ self.R.T + self.t


    def inverse(self):

        inv = RigidTransform()

        inv.R = self.R.T

        inv.t = -(self.R.T @ self.t)

        return inv


class InertiaTensor:

    def compute(self, verts):

        center = torch.mean(verts, dim=0)

        v = verts - center

        I = torch.zeros((3,3))

        for p in v:

            x,y,z = p

            I[0,0] += y*y + z*z
            I[1,1] += x*x + z*z
            I[2,2] += x*x + y*y

            I[0,1] -= x*y
            I[0,2] -= x*z
            I[1,2] -= y*z

        I[1,0] = I[0,1]
        I[2,0] = I[0,2]
        I[2,1] = I[1,2]

        return I


class SpectralGeometry:

    def laplacian(self, verts, faces):

        n = len(verts)

        L = torch.zeros((n,n))

        for f in faces:

            i,j,k = f

            L[i,j] = -1
            L[j,i] = -1

            L[j,k] = -1
            L[k,j] = -1

            L[k,i] = -1
            L[i,k] = -1

        for i in range(n):

            L[i,i] = -torch.sum(L[i])

        return L


    def spectrum(self, verts, faces):

        L = self.laplacian(verts, faces)

        vals, vecs = torch.linalg.eigh(L)

        return vals, vecs


class GramSchmidt:

    def orthogonalize(self, V):

        U = []

        for v in V:

            u = v.clone()

            for prev in U:

                proj = torch.dot(u, prev) * prev
                u = u - proj

            u = u / torch.linalg.norm(u)

            U.append(u)

        return torch.stack(U)


class AffineFitter:

    def fit(self, A, B):

        Amean = torch.mean(A, dim=0)
        Bmean = torch.mean(B, dim=0)

        Ac = A - Amean
        Bc = B - Bmean

        H = Ac.T @ Bc

        U,S,V = torch.linalg.svd(H)

        R = V.T @ U.T

        t = Bmean - R @ Amean

        return R, t


class LinearSystem:

    def solve(self, A, b):

        return torch.linalg.solve(A, b)


    def least_squares(self, A, b):

        return torch.linalg.lstsq(A, b).solution


class KernelLinearAlgebra:

    def __init__(self):

        self.eigen = EigenSolver()

        self.svd = SVD()

        self.pca = PCA()

        self.basis = OrthonormalBasis()

        self.quaternion = Quaternion()

        self.rigid = RigidTransform()

        self.inertia = InertiaTensor()

        self.spectral = SpectralGeometry()

        self.gram = GramSchmidt()

        self.affine = AffineFitter()

        self.linear = LinearSystem()


    def principal_axes(self, verts):

        pts = torch.tensor(verts)

        vals, vecs = self.pca.fit(pts)

        return vals, vecs


    def align_to_principal(self, verts):

        vals, vecs = self.principal_axes(verts)

        R = vecs

        pts = torch.tensor(verts)

        aligned = pts @ R

        return aligned
import torch
import math


class SDFBase:

    def __call__(self, p):

        return self.eval(p)


    def eval(self, p):

        raise NotImplementedError()


    def gradient(self, p, eps=1e-4):

        g = torch.zeros_like(p)

        for i in range(3):

            d = torch.zeros_like(p)

            d[:, i] = eps

            g[:, i] = (self.eval(p + d) - self.eval(p - d)) / (2 * eps)

        return g


    def hessian(self, p, eps=1e-4):

        H = torch.zeros((p.shape[0], 3, 3), device=p.device)

        for i in range(3):

            for j in range(3):

                d1 = torch.zeros_like(p)
                d2 = torch.zeros_like(p)

                d1[:, i] = eps
                d2[:, j] = eps

                H[:, i, j] = (
                    self.eval(p + d1 + d2)
                    - self.eval(p + d1 - d2)
                    - self.eval(p - d1 + d2)
                    + self.eval(p - d1 - d2)
                ) / (4 * eps * eps)

        return H


class Sphere(SDFBase):

    def __init__(self, r):

        self.r = r


    def eval(self, p):

        return torch.linalg.norm(p, dim=-1) - self.r


class Box(SDFBase):

    def __init__(self, size):

        self.size = torch.tensor(size)


    def eval(self, p):

        q = torch.abs(p) - self.size

        return torch.linalg.norm(torch.clamp(q, min=0), dim=-1) + torch.clamp(
            q.max(dim=-1).values, max=0
        )


class Cylinder(SDFBase):

    def __init__(self, r, h):

        self.r = r
        self.h = h


    def eval(self, p):

        d = torch.stack(
            [
                torch.linalg.norm(p[..., :2], dim=-1) - self.r,
                torch.abs(p[..., 2]) - self.h / 2,
            ],
            dim=-1,
        )

        return torch.minimum(
            torch.maximum(d[..., 0], d[..., 1]),
            torch.zeros_like(d[..., 0]),
        ) + torch.linalg.norm(torch.clamp(d, min=0), dim=-1)


class Torus(SDFBase):

    def __init__(self, R, r):

        self.R = R
        self.r = r


    def eval(self, p):

        q = torch.stack(
            [
                torch.linalg.norm(p[..., :2], dim=-1) - self.R,
                p[..., 2],
            ],
            dim=-1,
        )

        return torch.linalg.norm(q, dim=-1) - self.r


class Capsule(SDFBase):

    def __init__(self, a, b, r):

        self.a = torch.tensor(a)
        self.b = torch.tensor(b)
        self.r = r


    def eval(self, p):

        pa = p - self.a
        ba = self.b - self.a

        h = torch.clamp(
            torch.sum(pa * ba, dim=-1) / torch.sum(ba * ba), 0.0, 1.0
        )

        return torch.linalg.norm(pa - ba * h.unsqueeze(-1), dim=-1) - self.r


class Plane(SDFBase):

    def __init__(self, normal, d):

        self.normal = torch.tensor(normal)
        self.d = d


    def eval(self, p):

        return torch.sum(p * self.normal, dim=-1) + self.d


class Union(SDFBase):

    def __init__(self, a, b):

        self.a = a
        self.b = b


    def eval(self, p):

        return torch.minimum(self.a(p), self.b(p))


class Intersection(SDFBase):

    def __init__(self, a, b):

        self.a = a
        self.b = b


    def eval(self, p):

        return torch.maximum(self.a(p), self.b(p))


class Subtraction(SDFBase):

    def __init__(self, a, b):

        self.a = a
        self.b = b


    def eval(self, p):

        return torch.maximum(self.a(p), -self.b(p))


class SmoothUnion(SDFBase):

    def __init__(self, a, b, k):

        self.a = a
        self.b = b
        self.k = k


    def eval(self, p):

        da = self.a(p)
        db = self.b(p)

        h = torch.clamp(0.5 + 0.5 * (db - da) / self.k, 0, 1)

        return torch.lerp(db, da, h) - self.k * h * (1 - h)


class SmoothSubtraction(SDFBase):

    def __init__(self, a, b, k):

        self.a = a
        self.b = b
        self.k = k


    def eval(self, p):

        da = self.a(p)
        db = -self.b(p)

        h = torch.clamp(0.5 + 0.5 * (db - da) / self.k, 0, 1)

        return torch.lerp(db, da, h) - self.k * h * (1 - h)


class TransformSDF(SDFBase):

    def __init__(self, sdf, matrix):

        self.sdf = sdf
        self.matrix = matrix
        self.inv = torch.inverse(matrix)


    def eval(self, p):

        ones = torch.ones((p.shape[0], 1), device=p.device)

        ph = torch.cat([p, ones], dim=1)

        pt = (self.inv @ ph.T).T[:, :3]

        return self.sdf(pt)


class Repeat(SDFBase):

    def __init__(self, sdf, cell):

        self.sdf = sdf
        self.cell = torch.tensor(cell)


    def eval(self, p):

        q = torch.remainder(p + 0.5 * self.cell, self.cell) - 0.5 * self.cell

        return self.sdf(q)


class Twist(SDFBase):

    def __init__(self, sdf, k):

        self.sdf = sdf
        self.k = k


    def eval(self, p):

        angle = self.k * p[:, 2]

        c = torch.cos(angle)
        s = torch.sin(angle)

        x = c * p[:, 0] - s * p[:, 1]
        y = s * p[:, 0] + c * p[:, 1]

        pt = torch.stack([x, y, p[:, 2]], dim=1)

        return self.sdf(pt)


class Bend(SDFBase):

    def __init__(self, sdf, k):

        self.sdf = sdf
        self.k = k


    def eval(self, p):

        c = torch.cos(self.k * p[:, 0])
        s = torch.sin(self.k * p[:, 0])

        y = c * p[:, 1] - s * p[:, 2]
        z = s * p[:, 1] + c * p[:, 2]

        pt = torch.stack([p[:, 0], y, z], dim=1)

        return self.sdf(pt)


class NoiseDisplacement(SDFBase):

    def __init__(self, sdf, amp):

        self.sdf = sdf
        self.amp = amp


    def noise(self, p):

        return torch.sin(p[:,0]*10)*torch.sin(p[:,1]*10)*torch.sin(p[:,2]*10)


    def eval(self, p):

        return self.sdf(p) + self.noise(p) * self.amp


class Curvature:

    def mean(self, sdf, p):

        g = sdf.gradient(p)

        n = g / torch.linalg.norm(g, dim=-1, keepdim=True)

        div = torch.zeros(p.shape[0])

        eps = 1e-4

        for i in range(3):

            d = torch.zeros_like(p)

            d[:, i] = eps

            ni = sdf.gradient(p + d)
            ni = ni / torch.linalg.norm(ni, dim=-1, keepdim=True)

            div += (ni[:, i] - n[:, i]) / eps

        return div


    def gaussian(self, sdf, p):

        H = sdf.hessian(p)

        g = sdf.gradient(p)

        n = g / torch.linalg.norm(g, dim=-1, keepdim=True)

        K = torch.zeros(p.shape[0])

        for i in range(p.shape[0]):

            Hn = H[i]

            K[i] = torch.det(Hn)

        return K


class SDFLibrary:

    def __init__(self):

        self.curvature = Curvature()


    def sphere(self, r):

        return Sphere(r)


    def box(self, size):

        return Box(size)


    def cylinder(self, r, h):

        return Cylinder(r, h)


    def torus(self, R, r):

        return Torus(R, r)


    def capsule(self, a, b, r):

        return Capsule(a, b, r)
import hashlib
import torch
import json
import uuid


class GraphNode:

    def __init__(self, op, inputs=None, params=None):

        self.id = str(uuid.uuid4())
        self.op = op
        self.inputs = inputs if inputs else []
        self.params = params if params else {}
        self.cache = None


class GraphParameter:

    def __init__(self, name, value):

        self.name = name
        self.value = value


class GraphCache:

    def __init__(self):

        self.storage = {}

    def get(self, key):

        return self.storage.get(key)

    def set(self, key, value):

        self.storage[key] = value

    def clear(self):

        self.storage = {}


class GraphHasher:

    def hash_node(self, node):

        s = node.op + str(node.params)

        for inp in node.inputs:
            s += inp.id

        return hashlib.md5(s.encode()).hexdigest()

    def hash_graph(self, nodes):

        s = ""

        for n in nodes:
            s += self.hash_node(n)

        return hashlib.md5(s.encode()).hexdigest()


class GraphExecutor:

    def __init__(self, sdf_library):

        self.sdf = sdf_library
        self.cache = GraphCache()

    def execute_node(self, node, p):

        key = node.id

        if node.cache is not None:
            return node.cache(p)

        if node.op == "sphere":

            r = node.params["r"]
            fn = self.sdf.sphere(r)

        elif node.op == "box":

            size = node.params["size"]
            fn = self.sdf.box(size)

        elif node.op == "cylinder":

            fn = self.sdf.cylinder(node.params["r"], node.params["h"])

        elif node.op == "torus":

            fn = self.sdf.torus(node.params["R"], node.params["r"])

        elif node.op == "union":

            a = self.execute_node(node.inputs[0], p)
            b = self.execute_node(node.inputs[1], p)
            return torch.minimum(a, b)

        elif node.op == "subtract":

            a = self.execute_node(node.inputs[0], p)
            b = self.execute_node(node.inputs[1], p)
            return torch.maximum(a, -b)

        elif node.op == "intersect":

            a = self.execute_node(node.inputs[0], p)
            b = self.execute_node(node.inputs[1], p)
            return torch.maximum(a, b)

        elif node.op == "smooth_union":

            a = self.execute_node(node.inputs[0], p)
            b = self.execute_node(node.inputs[1], p)

            k = node.params["k"]

            h = torch.clamp(0.5 + 0.5 * (b - a) / k, 0, 1)

            return torch.lerp(b, a, h) - k * h * (1 - h)

        elif node.op == "twist":

            sdf = self.execute_node(node.inputs[0], p)

            k = node.params["k"]

            angle = k * p[:, 2]

            c = torch.cos(angle)
            s = torch.sin(angle)

            x = c * p[:, 0] - s * p[:, 1]
            y = s * p[:, 0] + c * p[:, 1]

            pt = torch.stack([x, y, p[:, 2]], dim=1)

            return sdf(pt)

        elif node.op == "repeat":

            sdf = self.execute_node(node.inputs[0], p)

            cell = torch.tensor(node.params["cell"])

            q = torch.remainder(p + 0.5 * cell, cell) - 0.5 * cell

            return sdf(q)

        else:

            raise ValueError("Unknown graph op")

        node.cache = fn

        return fn(p)


class SDFGraph:

    def __init__(self):

        self.nodes = []
        self.parameters = {}
        self.root = None

    def add_parameter(self, name, value):

        self.parameters[name] = GraphParameter(name, value)

    def node(self, op, inputs=None, **params):

        n = GraphNode(op, inputs, params)

        self.nodes.append(n)

        return n

    def set_root(self, node):

        self.root = node

    def clear_cache(self):

        for n in self.nodes:
            n.cache = None

    def evaluate(self, executor, p):

        if self.root is None:
            raise ValueError("Graph has no root")

        return executor.execute_node(self.root, p)


class GraphCompiler:

    def __init__(self, graph):

        self.graph = graph
        self.hasher = GraphHasher()

    def compile(self):

        h = self.hasher.hash_graph(self.graph.nodes)

        def compiled(p):

            executor = GraphExecutor(SDFLibrary())

            return self.graph.evaluate(executor, p)

        return compiled, h


class GraphSerializer:

    def save(self, graph, path):

        data = []

        for n in graph.nodes:

            entry = {
                "id": n.id,
                "op": n.op,
                "params": n.params,
                "inputs": [i.id for i in n.inputs]
            }

            data.append(entry)

        with open(path, "w") as f:
            json.dump(data, f)


class GraphDeserializer:

    def load(self, path):

        with open(path) as f:
            data = json.load(f)

        nodes = {}

        for entry in data:

            nodes[entry["id"]] = GraphNode(
                entry["op"], [], entry["params"]
            )

        for entry in data:

            node = nodes[entry["id"]]

            node.inputs = [nodes[i] for i in entry["inputs"]]

        graph = SDFGraph()

        graph.nodes = list(nodes.values())

        graph.root = graph.nodes[-1]

        return graph


class GraphOptimizer:

    def remove_unused(self, graph):

        used = set()

        def visit(n):

            if n.id in used:
                return

            used.add(n.id)

            for i in n.inputs:
                visit(i)

        visit(graph.root)

        graph.nodes = [n for n in graph.nodes if n.id in used]

    def constant_fold(self, graph):

        for n in graph.nodes:

            if n.op == "sphere" and n.params["r"] == 0:

                n.op = "constant"
                n.params = {"value": 0}


class GraphStats:

    def compute(self, graph):

        ops = {}

        for n in graph.nodes:

            if n.op not in ops:
                ops[n.op] = 0

            ops[n.op] += 1

        return {
            "node_count": len(graph.nodes),
            "ops": ops
        }


class KernelGraphLayer:

    def __init__(self):

        self.graph = None

    def new_graph(self):

        self.graph = SDFGraph()

        return self.graph

    def compile(self):

        compiler = GraphCompiler(self.graph)

        return compiler.compile()

    def stats(self):

        return GraphStats().compute(self.graph)
import torch
import numpy as np
from skimage import measure


class VoxelGrid:

    def __init__(self, resolution, bounds):

        self.resolution = resolution
        self.bounds = bounds

        self.x = torch.linspace(-bounds, bounds, resolution)
        self.y = torch.linspace(-bounds, bounds, resolution)
        self.z = torch.linspace(-bounds, bounds, resolution)

        grid = torch.meshgrid(self.x, self.y, self.z, indexing="ij")

        self.points = torch.stack(grid, dim=-1)


class FieldSampler:

    def __init__(self, sdf):

        self.sdf = sdf


    def sample(self, points):

        flat = points.reshape(-1, 3)

        values = self.sdf(flat)

        return values.reshape(points.shape[:-1])


class ChunkSampler:

    def __init__(self, sdf, chunk_size=500000):

        self.sdf = sdf
        self.chunk = chunk_size


    def sample(self, points):

        flat = points.reshape(-1, 3)

        vals = []

        for i in range(0, flat.shape[0], self.chunk):

            chunk = flat[i:i+self.chunk]

            vals.append(self.sdf(chunk))

        return torch.cat(vals).reshape(points.shape[:-1])


class MarchingCubes:

    def extract(self, volume, bounds):

        verts, faces, normals, _ = measure.marching_cubes(volume, level=0)

        res = volume.shape[0]

        verts = verts / (res - 1)

        verts = verts * (2 * bounds) - bounds

        return verts, faces, normals


class MeshBuffer:

    def __init__(self):

        self.verts = []
        self.faces = []
        self.normals = []


    def append(self, v, f, n=None):

        offset = len(self.verts)

        self.verts.extend(v)

        self.faces.extend(f + offset)

        if n is not None:
            self.normals.extend(n)


    def build(self):

        mesh = {
            "verts": np.array(self.verts),
            "faces": np.array(self.faces)
        }

        if self.normals:
            mesh["normals"] = np.array(self.normals)

        return mesh


class DualContouring:

    def __init__(self):

        self.vertices = []
        self.faces = []


    def qef(self, points, normals):

        A = torch.tensor(normals)

        b = torch.sum(A * torch.tensor(points), dim=1)

        x = torch.linalg.lstsq(A, b).solution

        return x


    def build(self, grid, sdf):

        res = grid.resolution

        verts = []

        for i in range(res-1):
            for j in range(res-1):
                for k in range(res-1):

                    p = grid.points[i,j,k]

                    d = sdf(p.unsqueeze(0))[0]

                    if abs(d) < 0.01:

                        verts.append(p.cpu().numpy())

        self.vertices = np.array(verts)

        return self.vertices


class AdaptiveGrid:

    def __init__(self, bounds, depth=4):

        self.bounds = bounds
        self.depth = depth


    def subdivide(self, sdf, center, size, level):

        d = sdf(center.unsqueeze(0))[0]

        if level >= self.depth or abs(d) < size:

            return [center]

        children = []

        step = size / 2

        for dx in [-step, step]:
            for dy in [-step, step]:
                for dz in [-step, step]:

                    c = center + torch.tensor([dx,dy,dz])

                    children.extend(
                        self.subdivide(sdf, c, step, level+1)
                    )

        return children


class MeshNormals:

    def compute(self, verts, faces):

        normals = np.zeros_like(verts)

        for f in faces:

            a,b,c = f

            v1 = verts[b] - verts[a]
            v2 = verts[c] - verts[a]

            n = np.cross(v1, v2)

            normals[a] += n
            normals[b] += n
            normals[c] += n

        norms = np.linalg.norm(normals, axis=1)

        normals = normals / norms[:,None]

        return normals


class MeshCleaner:

    def remove_degenerate(self, verts, faces):

        clean = []

        for f in faces:

            if len(set(f)) == 3:

                clean.append(f)

        return verts, np.array(clean)


    def remove_unreferenced(self, verts, faces):

        used = np.unique(faces.flatten())

        new_verts = verts[used]

        remap = {old:i for i,old in enumerate(used)}

        new_faces = np.array([[remap[i] for i in f] for f in faces])

        return new_verts, new_faces


class MeshDecimator:

    def decimate(self, mesh, target_ratio):

        verts = mesh["verts"]

        faces = mesh["faces"]

        target = int(len(faces) * target_ratio)

        if target >= len(faces):

            return mesh

        idx = np.random.choice(len(faces), target, replace=False)

        faces = faces[idx]

        return {
            "verts": verts,
            "faces": faces
        }


class MeshAnalyzer:

    def volume(self, verts, faces):

        vol = 0.0

        for f in faces:

            v0,v1,v2 = verts[f]

            vol += np.dot(v0, np.cross(v1,v2))

        return abs(vol)/6


    def surface_area(self, verts, faces):

        area = 0

        for f in faces:

            v0,v1,v2 = verts[f]

            area += np.linalg.norm(np.cross(v1-v0,v2-v0))/2

        return area


class MeshExporter:

    def export_stl(self, mesh, path):

        verts = mesh["verts"]
        faces = mesh["faces"]

        with open(path,"w") as f:

            f.write("solid mesh\n")

            for tri in faces:

                v0,v1,v2 = verts[tri]

                n = np.cross(v1-v0, v2-v0)

                f.write("facet normal {} {} {}\n".format(*n))
                f.write("outer loop\n")

                f.write("vertex {} {} {}\n".format(*v0))
                f.write("vertex {} {} {}\n".format(*v1))
                f.write("vertex {} {} {}\n".format(*v2))

                f.write("endloop\n")
                f.write("endfacet\n")

            f.write("endsolid\n")


class KernelMeshingLayer:

    def __init__(self):

        self.marching = MarchingCubes()

        self.cleaner = MeshCleaner()

        self.normals = MeshNormals()

        self.decimator = MeshDecimator()

        self.analyzer = MeshAnalyzer()

        self.exporter = MeshExporter()


    def build_mesh(self, sdf, resolution=128, bounds=2):

        grid = VoxelGrid(resolution, bounds)

        sampler = ChunkSampler(sdf)

        volume = sampler.sample(grid.points)

        volume = volume.cpu().numpy()

        verts, faces, normals = self.marching.extract(volume, bounds)

        verts, faces = self.cleaner.remove_degenerate(verts, faces)

        verts, faces = self.cleaner.remove_unreferenced(verts, faces)

        return {
            "verts": verts,
            "faces": faces,
            "normals": normals
        }

import torch
import numpy as np
import math


class OctreeNode:

    def __init__(self, center, size, level=0):

        self.center = center
        self.size = size
        self.level = level

        self.children = None

        self.value = None

        self.is_leaf = True


class Octree:

    def __init__(self, sdf, max_depth=6, threshold=0.01):

        self.sdf = sdf
        self.max_depth = max_depth
        self.threshold = threshold

        self.root = None


    def build(self, bounds):

        center = torch.tensor([0.0,0.0,0.0])

        self.root = OctreeNode(center, bounds)

        self.subdivide(self.root)


    def subdivide(self, node):

        d = self.sdf(node.center.unsqueeze(0))[0]

        node.value = d

        if node.level >= self.max_depth:

            return

        if abs(d) > node.size:

            return

        node.children = []

        node.is_leaf = False

        step = node.size / 2

        for dx in [-step, step]:
            for dy in [-step, step]:
                for dz in [-step, step]:

                    c = node.center + torch.tensor([dx,dy,dz])

                    child = OctreeNode(
                        c,
                        step,
                        node.level + 1
                    )

                    node.children.append(child)

                    self.subdivide(child)


class OctreeTraversal:

    def collect_leaves(self, node):

        leaves = []

        if node.is_leaf:

            leaves.append(node)

        else:

            for c in node.children:

                leaves.extend(self.collect_leaves(c))

        return leaves


class SparseField:

    def __init__(self):

        self.points = []
        self.values = []


    def insert(self, p, v):

        self.points.append(p)

        self.values.append(v)


    def build(self):

        return {
            "points": np.array(self.points),
            "values": np.array(self.values)
        }


class SparseSampler:

    def __init__(self, sdf):

        self.sdf = sdf


    def sample_points(self, pts):

        vals = self.sdf(pts)

        return vals


class MultiResolutionField:

    def __init__(self, sdf):

        self.sdf = sdf

        self.levels = {}


    def build_level(self, res, bounds):

        xs = torch.linspace(-bounds, bounds, res)

        grid = torch.meshgrid(xs, xs, xs, indexing="ij")

        pts = torch.stack(grid, dim=-1)

        flat = pts.reshape(-1,3)

        vals = self.sdf(flat)

        self.levels[res] = vals.reshape(res,res,res)


    def get(self, res):

        return self.levels.get(res)


class SpatialQuery:

    def nearest(self, pts, p):

        d = np.linalg.norm(pts - p, axis=1)

        idx = np.argmin(d)

        return pts[idx]


    def radius(self, pts, p, r):

        d = np.linalg.norm(pts - p, axis=1)

        mask = d < r

        return pts[mask]


class OctreeFieldExtractor:

    def __init__(self, sdf):

        self.sdf = sdf


    def extract_points(self, octree):

        traversal = OctreeTraversal()

        leaves = traversal.collect_leaves(octree.root)

        pts = []

        vals = []

        for leaf in leaves:

            pts.append(leaf.center.numpy())

            vals.append(leaf.value)

        return np.array(pts), np.array(vals)


class LODField:

    def __init__(self, sdf):

        self.sdf = sdf

        self.levels = {}


    def build(self, resolutions, bounds):

        for r in resolutions:

            xs = torch.linspace(-bounds, bounds, r)

            grid = torch.meshgrid(xs,xs,xs,indexing="ij")

            pts = torch.stack(grid,dim=-1)

            flat = pts.reshape(-1,3)

            vals = self.sdf(flat)

            self.levels[r] = vals.reshape(r,r,r)


    def query(self, p, res):

        field = self.levels.get(res)

        if field is None:

            return None

        size = field.shape[0]

        idx = ((p+1)/2 * (size-1)).astype(int)

        return field[idx[0],idx[1],idx[2]]


class SparseVoxelGrid:

    def __init__(self, voxel_size):

        self.voxel = voxel_size

        self.data = {}


    def key(self, p):

        return tuple((p / self.voxel).astype(int))


    def insert(self, p, value):

        k = self.key(p)

        self.data[k] = value


    def query(self, p):

        k = self.key(p)

        return self.data.get(k)


class SurfaceSampler:

    def __init__(self, sdf):

        self.sdf = sdf


    def sample_surface(self, count=10000):

        pts = torch.rand(count,3)*2-1

        vals = self.sdf(pts)

        mask = torch.abs(vals) < 0.01

        return pts[mask]


class DistanceField:

    def __init__(self, sdf):

        self.sdf = sdf


    def evaluate(self, pts):

        return self.sdf(pts)


    def gradient(self, pts):

        eps = 1e-4

        g = torch.zeros_like(pts)

        for i in range(3):

            d = torch.zeros_like(pts)

            d[:,i] = eps

            g[:,i] = (self.sdf(pts+d)-self.sdf(pts-d))/(2*eps)

        return g


class FieldCompression:

    def quantize(self, field, bits=16):

        maxv = np.max(np.abs(field))

        scale = (2**(bits-1)-1)/maxv

        q = np.round(field*scale).astype(np.int16)

        return q, scale


    def decompress(self, q, scale):

        return q.astype(float)/scale


class KernelSparseLayer:

    def __init__(self):

        self.octree = None


    def build_octree(self, sdf, bounds, depth=6):

        tree = Octree(sdf, depth)

        tree.build(bounds)

        self.octree = tree

        return tree


    def extract_sparse(self):

        extractor = OctreeFieldExtractor(self.octree.sdf)

        return extractor.extract_points(self.octree)
    
    import torch
import numpy as np


class Parameter:

    def __init__(self, name, value):

        self.name = name
        self.value = float(value)

        self.dependents = []


    def set(self, v):

        self.value = float(v)

        for d in self.dependents:

            d.mark_dirty()


class ParameterRegistry:

    def __init__(self):

        self.params = {}


    def create(self, name, value):

        p = Parameter(name, value)

        self.params[name] = p

        return p


    def get(self, name):

        return self.params[name]


    def values(self):

        return {k:v.value for k,v in self.params.items()}


class Constraint:

    def __init__(self, fn):

        self.fn = fn


    def evaluate(self, params):

        return self.fn(params)


class ConstraintSystem:

    def __init__(self):

        self.constraints = []

        self.parameters = []


    def add_parameter(self, p):

        self.parameters.append(p)


    def add_constraint(self, c):

        self.constraints.append(c)


    def vector(self):

        return torch.tensor([p.value for p in self.parameters])


    def apply(self, vec):

        for i,p in enumerate(self.parameters):

            p.value = float(vec[i])


    def residuals(self):

        params = {p.name:p.value for p in self.parameters}

        r = []

        for c in self.constraints:

            r.append(c.evaluate(params))

        return torch.tensor(r)


class Jacobian:

    def compute(self, system, eps=1e-6):

        x = system.vector()

        f0 = system.residuals()

        m = len(f0)

        n = len(x)

        J = torch.zeros(m,n)

        for i in range(n):

            dx = torch.zeros(n)

            dx[i] = eps

            system.apply(x+dx)

            f1 = system.residuals()

            J[:,i] = (f1-f0)/eps

            system.apply(x)

        return J


class NewtonSolver:

    def __init__(self, iterations=20):

        self.iterations = iterations


    def solve(self, system):

        jac = Jacobian()

        x = system.vector()

        for _ in range(self.iterations):

            r = system.residuals()

            J = jac.compute(system)

            step = torch.linalg.lstsq(J, -r).solution

            x = x + step

            system.apply(x)

            if torch.norm(r) < 1e-6:

                break

        return x


class GaussNewtonSolver:

    def __init__(self, iterations=20):

        self.iterations = iterations


    def solve(self, system):

        jac = Jacobian()

        x = system.vector()

        for _ in range(self.iterations):

            r = system.residuals()

            J = jac.compute(system)

            JT = J.T

            step = torch.linalg.solve(JT@J, -JT@r)

            x = x + step

            system.apply(x)

            if torch.norm(r) < 1e-6:

                break

        return x


class ConstraintGraph:

    def __init__(self):

        self.nodes = []


    def add(self, node):

        self.nodes.append(node)


    def evaluate(self):

        for n in self.nodes:

            n.evaluate()


class FeatureNode:

    def __init__(self, fn):

        self.fn = fn

        self.dirty = True

        self.output = None


    def mark_dirty(self):

        self.dirty = True


    def evaluate(self):

        if self.dirty:

            self.output = self.fn()

            self.dirty = False

        return self.output


class HistoryGraph:

    def __init__(self):

        self.features = []


    def add_feature(self, node):

        self.features.append(node)


    def build(self):

        result = None

        for f in self.features:

            result = f.evaluate()

        return result


class ParametricPrimitive:

    def __init__(self, kernel):

        self.kernel = kernel


    def sphere(self, r_param):

        def sdf(p):

            r = r_param.value

            return torch.linalg.norm(p,dim=-1)-r

        return sdf


    def box(self, sx, sy, sz):

        def sdf(p):

            size = torch.tensor([sx.value, sy.value, sz.value])

            q = torch.abs(p)-size

            return torch.linalg.norm(torch.clamp(q,min=0),dim=-1) + \
                   torch.clamp(q.max(dim=-1).values,max=0)

        return sdf


class ParametricTransform:

    def translate(self, sdf, tx, ty, tz):

        def f(p):

            t = torch.tensor([tx.value,ty.value,tz.value])

            return sdf(p-t)

        return f


    def scale(self, sdf, s):

        def f(p):

            return sdf(p/s.value)*s.value

        return f


class ParameterExpression:

    def __init__(self, fn):

        self.fn = fn


    def evaluate(self, params):

        return self.fn(params)


class DependencyGraph:

    def __init__(self):

        self.nodes = {}

        self.edges = {}


    def add_node(self, name, fn):

        self.nodes[name] = fn

        self.edges[name] = []


    def connect(self, a, b):

        self.edges[a].append(b)


    def evaluate(self, start):

        visited = set()

        order = []

        def dfs(n):

            if n in visited:

                return

            visited.add(n)

            for m in self.edges[n]:

                dfs(m)

            order.append(n)

        dfs(start)

        result = None

        for n in order:

            result = self.nodes[n]()

        return result


class ParametricGraphBuilder:

    def __init__(self):

        self.registry = ParameterRegistry()

        self.history = HistoryGraph()

        self.constraints = ConstraintSystem()


    def parameter(self, name, value):

        p = self.registry.create(name,value)

        self.constraints.add_parameter(p)

        return p


    def constraint(self, fn):

        self.constraints.add_constraint(Constraint(fn))


    def feature(self, fn):

        node = FeatureNode(fn)

        self.history.add_feature(node)

        return node


    def solve(self):

        solver = NewtonSolver()

        solver.solve(self.constraints)


class GeometryOptimizer:

    def minimize(self, fn, x0, lr=0.01, iters=100):

        x = torch.tensor(x0,dtype=torch.float32)

        x.requires_grad=True

        opt = torch.optim.Adam([x],lr=lr)

        for _ in range(iters):

            opt.zero_grad()

            loss = fn(x)

            loss.backward()

            opt.step()

        return x.detach()


class SensitivityAnalysis:

    def gradient(self, fn, x):

        x = torch.tensor(x,dtype=torch.float32,requires_grad=True)

        y = fn(x)

        y.backward()

        return x.grad


class KernelParametricLayer:

    def __init__(self):

        self.builder = ParametricGraphBuilder()


    def parameter(self,name,value):

        return self.builder.parameter(name,value)


    def constraint(self,fn):

        self.builder.constraint(fn)


    def solve(self):

        self.builder.solve()


    def build(self):

        return self.builder.history.build()
    
    import numpy as np
import torch


class MeshAdjacency:

    def build_vertex_neighbors(self, faces, nverts):

        neighbors = [[] for _ in range(nverts)]

        for f in faces:

            a,b,c = f

            neighbors[a].extend([b,c])
            neighbors[b].extend([a,c])
            neighbors[c].extend([a,b])

        for i in range(nverts):

            neighbors[i] = list(set(neighbors[i]))

        return neighbors


    def build_edge_list(self, faces):

        edges = set()

        for f in faces:

            a,b,c = f

            edges.add(tuple(sorted((a,b))))
            edges.add(tuple(sorted((b,c))))
            edges.add(tuple(sorted((c,a))))

        return list(edges)


class FaceNormals:

    def compute(self, verts, faces):

        n = []

        for f in faces:

            v0,v1,v2 = verts[f]

            nrm = np.cross(v1-v0, v2-v0)

            nrm = nrm / (np.linalg.norm(nrm)+1e-12)

            n.append(nrm)

        return np.array(n)


class VertexNormals:

    def compute(self, verts, faces):

        nverts = len(verts)

        normals = np.zeros((nverts,3))

        fn = FaceNormals().compute(verts,faces)

        for i,f in enumerate(faces):

            for v in f:

                normals[v] += fn[i]

        norms = np.linalg.norm(normals,axis=1)

        normals = normals/(norms[:,None]+1e-12)

        return normals


class CotangentWeights:

    def compute(self, verts, faces):

        weights = {}

        for f in faces:

            i,j,k = f

            vi,vj,vk = verts[i],verts[j],verts[k]

            a = vj-vi
            b = vk-vi

            cot = np.dot(a,b)/(np.linalg.norm(np.cross(a,b))+1e-12)

            weights[(j,k)] = weights.get((j,k),0)+cot
            weights[(k,j)] = weights.get((k,j),0)+cot

        return weights


class LaplaceBeltrami:

    def build_matrix(self, verts, faces):

        n = len(verts)

        W = np.zeros((n,n))

        weights = CotangentWeights().compute(verts,faces)

        for (i,j),w in weights.items():

            W[i,j] = w

        for i in range(n):

            W[i,i] = -np.sum(W[i])

        return W


class MeanCurvature:

    def compute(self, verts, faces):

        L = LaplaceBeltrami().build_matrix(verts,faces)

        v = verts

        H = L @ v

        mag = np.linalg.norm(H,axis=1)

        return mag


class ShapeOperator:

    def compute(self, verts, faces):

        normals = VertexNormals().compute(verts,faces)

        adj = MeshAdjacency().build_vertex_neighbors(faces,len(verts))

        operators = []

        for i,v in enumerate(verts):

            n = normals[i]

            M = np.zeros((3,3))

            for j in adj[i]:

                d = verts[j]-v

                dn = normals[j]-n

                M += np.outer(d,dn)

            operators.append(M)

        return operators


class PrincipalCurvature:

    def compute(self, verts, faces):

        ops = ShapeOperator().compute(verts,faces)

        k1 = []
        k2 = []

        dirs1 = []
        dirs2 = []

        for M in ops:

            w,v = np.linalg.eig(M)

            idx = np.argsort(w)

            k1.append(w[idx[-1]])
            k2.append(w[idx[0]])

            dirs1.append(v[:,idx[-1]])
            dirs2.append(v[:,idx[0]])

        return np.array(k1), np.array(k2), np.array(dirs1), np.array(dirs2)


class GeodesicDistance:

    def compute(self, verts, faces, source):

        adj = MeshAdjacency().build_vertex_neighbors(faces,len(verts))

        dist = np.full(len(verts), np.inf)

        dist[source] = 0

        Q = [source]

        while Q:

            v = Q.pop(0)

            for n in adj[v]:

                d = np.linalg.norm(verts[n]-verts[v])

                nd = dist[v]+d

                if nd < dist[n]:

                    dist[n] = nd

                    Q.append(n)

        return dist


class HeatDiffusion:

    def diffuse(self, verts, faces, values, t=0.01):

        L = LaplaceBeltrami().build_matrix(verts,faces)

        A = np.eye(len(verts)) - t*L

        return np.linalg.solve(A, values)


class GradientField:

    def compute(self, verts, faces, scalar):

        grad = np.zeros((len(faces),3))

        for i,f in enumerate(faces):

            v0,v1,v2 = verts[f]

            s0,s1,s2 = scalar[f]

            e1 = v1-v0
            e2 = v2-v0

            grad[i] = (s1-s0)*e1 + (s2-s0)*e2

        return grad


class DivergenceField:

    def compute(self, verts, faces, vector):

        div = np.zeros(len(verts))

        for i,f in enumerate(faces):

            for v in f:

                div[v] += np.dot(vector[i], vector[i])

        return div


class SpectralDecomposition:

    def eigen(self, verts, faces, k=20):

        L = LaplaceBeltrami().build_matrix(verts,faces)

        w,v = np.linalg.eigh(L)

        return w[:k], v[:,:k]


class HarmonicField:

    def solve(self, verts, faces, boundary_ids, boundary_vals):

        L = LaplaceBeltrami().build_matrix(verts,faces)

        b = np.zeros(len(verts))

        for i,v in zip(boundary_ids,boundary_vals):

            L[i,:]=0
            L[i,i]=1
            b[i]=v

        return np.linalg.solve(L,b)


class MeshSmoothing:

    def laplacian_smooth(self, verts, faces, iterations=10, alpha=0.5):

        adj = MeshAdjacency().build_vertex_neighbors(faces,len(verts))

        v = verts.copy()

        for _ in range(iterations):

            new = v.copy()

            for i in range(len(v)):

                nbs = adj[i]

                if not nbs:

                    continue

                avg = np.mean(v[nbs],axis=0)

                new[i] = v[i]*(1-alpha)+avg*alpha

            v = new

        return v


class SpectralEmbedding:

    def embed(self, verts, faces, dim=3):

        w,v = SpectralDecomposition().eigen(verts,faces,dim+1)

        return v[:,1:dim+1]


class KernelDifferentialLayer:

    def __init__(self):

        self.curvature = MeanCurvature()

        self.principal = PrincipalCurvature()

        self.spectral = SpectralDecomposition()

        self.geodesic = GeodesicDistance()

        self.smooth = MeshSmoothing()


    def curvature_field(self, verts, faces):

        return self.curvature.compute(verts,faces)


    def principal_curvature(self, verts, faces):

        return self.principal.compute(verts,faces)


    def spectral_modes(self, verts, faces, k=20):

        return self.spectral.eigen(verts,faces,k)


    def geodesic_distance(self, verts, faces, source):

        return self.geodesic.compute(verts,faces,source)


    def smooth_mesh(self, verts, faces):

        return self.smooth.laplacian_smooth(verts,faces)
    
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np


class FourierEncoding:

    def __init__(self, input_dim=3, num_frequencies=10):

        self.input_dim = input_dim
        self.freq = 2 ** torch.arange(num_frequencies).float()


    def encode(self, x):

        enc = [x]

        for f in self.freq:

            enc.append(torch.sin(f * x))
            enc.append(torch.cos(f * x))

        return torch.cat(enc, dim=-1)


class NeuralSDF(nn.Module):

    def __init__(self, hidden=128, layers=6, encoding_dim=63):

        super().__init__()

        modules = []

        in_dim = encoding_dim

        for i in range(layers):

            modules.append(nn.Linear(in_dim, hidden))
            modules.append(nn.ReLU())

            in_dim = hidden

        modules.append(nn.Linear(hidden, 1))

        self.net = nn.Sequential(*modules)


    def forward(self, x):

        return self.net(x)


class NeuralField:

    def __init__(self):

        self.encoder = FourierEncoding()

        self.model = NeuralSDF()

        self.optimizer = optim.Adam(self.model.parameters(), lr=1e-3)


    def sdf(self, pts):

        enc = self.encoder.encode(pts)

        return self.model(enc)


    def train_step(self, pts, target):

        self.optimizer.zero_grad()

        pred = self.sdf(pts)

        loss = ((pred - target)**2).mean()

        loss.backward()

        self.optimizer.step()

        return loss.item()


class NeuralSampler:

    def random_points(self, count):

        return torch.rand(count,3)*2-1


    def near_surface(self, sdf, count):

        pts = torch.rand(count*5,3)*2-1

        vals = sdf(pts)

        mask = torch.abs(vals)<0.05

        return pts[mask][:count]


class NeuralTrainer:

    def __init__(self, field):

        self.field = field

        self.sampler = NeuralSampler()


    def train_sdf(self, analytic_sdf, steps=2000, batch=4096):

        for i in range(steps):

            pts = self.sampler.random_points(batch)

            target = analytic_sdf(pts).unsqueeze(-1)

            loss = self.field.train_step(pts,target)

            if i%100==0:

                print("step",i,"loss",loss)


class NeuralSurfaceExtractor:

    def extract_points(self, field, count=10000):

        pts = torch.rand(count*5,3)*2-1

        vals = field.sdf(pts)

        mask = torch.abs(vals)<0.01

        return pts[mask]


class LatentShapeSpace(nn.Module):

    def __init__(self, latent_dim=32):

        super().__init__()

        self.latent = nn.Parameter(torch.randn(latent_dim))

        self.decoder = NeuralSDF(hidden=128,layers=5,encoding_dim=latent_dim+63)

        self.encoder = FourierEncoding()


    def forward(self, x):

        enc = self.encoder.encode(x)

        z = self.latent.expand(x.shape[0],-1)

        inp = torch.cat([enc,z],dim=-1)

        return self.decoder(inp)


class NeuralDeformationField(nn.Module):

    def __init__(self, hidden=128):

        super().__init__()

        self.net = nn.Sequential(
            nn.Linear(3,hidden),
            nn.ReLU(),
            nn.Linear(hidden,hidden),
            nn.ReLU(),
            nn.Linear(hidden,3)
        )


    def forward(self,x):

        return x + self.net(x)


class NeuralMeshRefiner:

    def refine(self, verts, sdf_fn, steps=10):

        v = torch.tensor(verts).float()

        for _ in range(steps):

            v.requires_grad=True

            d = sdf_fn(v)

            loss = (d**2).mean()

            loss.backward()

            v = v - 0.1*v.grad

        return v.detach().numpy()


class OccupancyNetwork(nn.Module):

    def __init__(self, hidden=128):

        super().__init__()

        self.net = nn.Sequential(
            nn.Linear(3,hidden),
            nn.ReLU(),
            nn.Linear(hidden,hidden),
            nn.ReLU(),
            nn.Linear(hidden,1),
            nn.Sigmoid()
        )


    def forward(self,x):

        return self.net(x)


class NeuralRegularizer:

    def eikonal(self, sdf_fn, pts):

        pts.requires_grad=True

        d = sdf_fn(pts)

        g = torch.autograd.grad(
            d,
            pts,
            grad_outputs=torch.ones_like(d),
            create_graph=True
        )[0]

        return ((g.norm(dim=-1)-1)**2).mean()


class NeuralFieldExporter:

    def export_weights(self, model, path):

        torch.save(model.state_dict(), path)


    def load_weights(self, model, path):

        model.load_state_dict(torch.load(path))


class NeuralDistanceField:

    def evaluate(self, model, pts):

        return model(pts)


class KernelNeuralLayer:

    def __init__(self):

        self.field = NeuralField()

        self.trainer = NeuralTrainer(self.field)

        self.extractor = NeuralSurfaceExtractor()

        self.refiner = NeuralMeshRefiner()

        self.reg = NeuralRegularizer()


    def train_from_sdf(self, sdf):

        self.trainer.train_sdf(sdf)


    def sample_surface(self):

        return self.extractor.extract_points(self.field)


    def refine_mesh(self, verts):

        return self.refiner.refine(verts,self.field.sdf)

import torch
import numpy as np
import threading
import queue


class DeviceManager:

    def __init__(self):

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )


    def to_device(self, tensor):

        return tensor.to(self.device)


    def tensor(self, data):

        return torch.tensor(data, device=self.device, dtype=torch.float32)


class TensorVoxelGrid:

    def __init__(self, resolution, bounds, device):

        self.res = resolution
        self.bounds = bounds
        self.device = device

        xs = torch.linspace(-bounds, bounds, resolution, device=device)

        grid = torch.meshgrid(xs, xs, xs, indexing="ij")

        self.points = torch.stack(grid, dim=-1)


class BatchedSDFEvaluator:

    def __init__(self, sdf, device):

        self.sdf = sdf
        self.device = device


    def evaluate(self, pts, batch=500000):

        pts = pts.reshape(-1,3)

        results = []

        for i in range(0, len(pts), batch):

            p = pts[i:i+batch].to(self.device)

            v = self.sdf(p)

            results.append(v.detach().cpu())

        return torch.cat(results)


class ParallelChunkSampler:

    def __init__(self, sdf, device):

        self.sdf = sdf
        self.device = device


    def sample(self, grid, chunk=500000):

        pts = grid.points.reshape(-1,3)

        eval = BatchedSDFEvaluator(self.sdf,self.device)

        vals = eval.evaluate(pts,chunk)

        return vals.reshape(grid.res,grid.res,grid.res)


class AsyncTask:

    def __init__(self, fn, *args):

        self.fn = fn
        self.args = args
        self.result = None


    def run(self):

        self.result = self.fn(*self.args)


class AsyncExecutor:

    def __init__(self, workers=4):

        self.q = queue.Queue()

        self.workers = []

        for _ in range(workers):

            t = threading.Thread(target=self.worker)

            t.daemon = True

            t.start()

            self.workers.append(t)


    def worker(self):

        while True:

            task = self.q.get()

            if task is None:

                break

            task.run()

            self.q.task_done()


    def submit(self, task):

        self.q.put(task)


    def wait(self):

        self.q.join()


class GPUFieldCache:

    def __init__(self):

        self.cache = {}


    def store(self, key, value):

        self.cache[key] = value


    def get(self, key):

        return self.cache.get(key)


class MultiGPUDispatcher:

    def __init__(self):

        self.devices = []

        if torch.cuda.is_available():

            for i in range(torch.cuda.device_count()):

                self.devices.append(torch.device(f"cuda:{i}"))


    def split_batches(self, pts):

        if not self.devices:

            return [pts]

        chunks = torch.chunk(pts,len(self.devices))

        return list(chunks)


    def dispatch(self, sdf, pts):

        chunks = self.split_batches(pts)

        outputs = []

        for dev,chunk in zip(self.devices,chunks):

            p = chunk.to(dev)

            v = sdf(p)

            outputs.append(v.cpu())

        return torch.cat(outputs)


class StreamingVoxelSampler:

    def __init__(self, sdf, device):

        self.sdf = sdf
        self.device = device


    def stream(self, resolution, bounds, chunk=64):

        xs = torch.linspace(-bounds,bounds,resolution)

        volume = torch.zeros((resolution,resolution,resolution))

        for i in range(0,resolution,chunk):

            for j in range(0,resolution,chunk):

                for k in range(0,resolution,chunk):

                    xi = xs[i:i+chunk]
                    yj = xs[j:j+chunk]
                    zk = xs[k:k+chunk]

                    grid = torch.meshgrid(xi,yj,zk,indexing="ij")

                    pts = torch.stack(grid,dim=-1).reshape(-1,3)

                    vals = self.sdf(pts.to(self.device)).cpu()

                    vals = vals.reshape(len(xi),len(yj),len(zk))

                    volume[
                        i:i+len(xi),
                        j:j+len(yj),
                        k:k+len(zk)
                    ] = vals

        return volume


class GPUMeshRefiner:

    def refine(self, verts, sdf, steps=8):

        v = torch.tensor(verts).float()

        for _ in range(steps):

            v.requires_grad=True

            d = sdf(v)

            loss = (d**2).mean()

            loss.backward()

            v = v - 0.1*v.grad

        return v.detach().cpu().numpy()


class TensorMarchingPrep:

    def prepare(self, volume):

        return torch.tensor(volume)


class KernelGPULayer:

    def __init__(self):

        self.devices = DeviceManager()

        self.cache = GPUFieldCache()

        self.dispatcher = MultiGPUDispatcher()


    def evaluate_sdf(self, sdf, pts):

        pts = self.devices.to_device(pts)

        vals = sdf(pts)

        return vals.detach().cpu()


    def build_volume(self, sdf, resolution, bounds):

        grid = TensorVoxelGrid(
            resolution,
            bounds,
            self.devices.device
        )

        sampler = ParallelChunkSampler(
            sdf,
            self.devices.device
        )

        return sampler.sample(grid)

import torch
import numpy as np
import scipy.linalg as la

# =========================================
# Eigenvector & Matrix Utilities
# =========================================
def eigen_decompose(matrix):
    vals, vecs = np.linalg.eigh(matrix)
    return vals, vecs

def principal_axes(points):
    """
    Compute covariance matrix and principal axes (eigenvectors)
    """
    centered = points - np.mean(points, axis=0)
    cov = np.cov(centered.T)
    vals, vecs = eigen_decompose(cov)
    return vals, vecs

def rotate_points(points, axis, theta):
    R = rotation_matrix(axis, theta)
    return points @ R.T

def shear_matrix(a, b, c):
    return np.array([[1, a, b],
                     [0, 1, c],
                     [0, 0, 1]])

# =========================================
# Advanced Procedural Noise
# =========================================
class cad_master_kernelSDFNoise:
    @staticmethod
    def perlin_noise(p):
        # simple torch-based 3D perlin
        return torch.sin(5*p[...,0]) * torch.cos(5*p[...,1]) * torch.sin(5*p[...,2])

    @staticmethod
    def simplex_noise(p):
        return torch.sin(10*p[...,0]*p[...,1]) * torch.cos(10*p[...,1]*p[...,2])

    @staticmethod
    def voronoi_noise(p):
        return torch.min(torch.abs(p[...,0]*3 - torch.round(p[...,0]*3)),
                         torch.abs(p[...,1]*3 - torch.round(p[...,1]*3)))

@classmethod
def fractal_noise(cls, p, octaves=4, lacunarity=2.0, gain=0.5):
    val = torch.zeros_like(p[..., 0])
    amplitude = 1.0
    frequency = 1.0

    for _ in range(octaves):
        val += amplitude * cls.perlin_noise(p * frequency)
        frequency *= lacunarity
        amplitude *= gain

    return val
    @staticmethod
    def perturb(sdf_fn, noise_fn, strength=0.05):
        def perturbed(p):
            return sdf_fn(p + noise_fn(p).unsqueeze(-1) * strength)
        return perturbed

# =========================================
# Advanced SDF Primitives
# =========================================
class SDFAdvanced(SDFPrimitives):
    def ellipsoid(self, p, radii):
        q = p / torch.tensor(radii, device=p.device)
        return torch.linalg.norm(q, dim=-1) - 1.0

    def hyperboloid(self, p, a, b, c):
        return ((p[...,0]/a)**2 + (p[...,1]/b)**2 - (p[...,2]/c)**2) - 1.0

    def prism(self, p, size, height):
        q = torch.stack([torch.abs(p[...,0]) - size[0],
                         torch.abs(p[...,1]) - size[1],
                         torch.abs(p[...,2]) - height/2], dim=-1)
        return torch.linalg.norm(torch.clamp(q, min=0), dim=-1) + torch.clamp(q.max(dim=-1).values, max=0)

# =========================================
# Recursive & Hierarchical Graph
# =========================================
class SDFRecursiveGraph(SDFGraph):
    def __init__(self, depth=1):
        super().__init__()
        self.depth = depth

    def build_recursive(self):
        sdf = self.build()
        if self.depth <= 1:
            return sdf
        def recursive_sdf(p):
            val = sdf(p)
            # recursive fractal scaling
            for i in range(1, self.depth):
                scale = 2**i
                val = torch.minimum(val, sdf(p * scale)/scale)
            return val
        return recursive_sdf

# =========================================
# Extended CADKernel
# =========================================
    def CADKernel(self):
        # build base graph
        base = super().CADKernel()
        # add advanced primitives
        self.advanced = SDFAdvanced()
        return base
    
    def primitive(self, name, **p):
        # include all previous
        base = super().primitive(name, **p)
        if name=="ellipsoid":
            return lambda x: self.advanced.ellipsoid(x, p.get("radii",[0.5,0.5,0.5]))
        if name=="hyperboloid":
            return lambda x: self.advanced.hyperboloid(x,
                                                       p.get("a",0.5),
                                                       p.get("b",0.5),
                                                       p.get("c",0.5))
        if name=="prism":
            return lambda x: self.advanced.prism(x, p.get("size",[0.5,0.5]), p.get("height",0.5))
        return base

    def principal_axes_mesh(self, mesh):
        pts = mesh["verts"]
        vals, vecs = principal_axes(np.array(pts))
        return vals, vecs

    def curvature_analysis(self, mesh):
        # rough curvature estimate using laplacian
        tm = trimesh.Trimesh(mesh["verts"], mesh["faces"])
        return {
            "mean_curvature": np.mean(tm.vertex_defects),
            "max_curvature": np.max(tm.vertex_defects)
        }

# =========================================
# Part 2 complete (~500 lines)
# ready to add fractal batch, Voronoi, Laplace-Beltrami, GPU batching in Part 3
# =========================================

# =========================================
# Part 3 — Fractal batch, Voronoi, Laplace-Beltrami, GPU batching
# =========================================

import math
import random
from collections import defaultdict

# -----------------------------------------
# Fractal Batch Generation
# -----------------------------------------

class FractalBatch:
    def __init__(self):
        self.points = []

    def mandelbrot(self, width, height, max_iter=100):
        result = []
        for x in range(width):
            for y in range(height):
                zx = 1.5*(x - width/2)/(0.5*width)
                zy = (y - height/2)/(0.5*height)
                cX, cY = zx, zy
                iter_count = max_iter
                while zx*zx + zy*zy < 4 and iter_count > 1:
                    tmp = zx*zx - zy*zy + cX
                    zy, zx = 2.0*zx*zy + cY, tmp
                    iter_count -= 1
                result.append((x, y, iter_count))
        return result

    def sierpinski(self, iterations=10000):
        x, y = 0.0, 0.0
        vertices = [(0,0), (1,0), (0.5,0.866)]
        pts = []
        for _ in range(iterations):
            vx, vy = random.choice(vertices)
            x = (x + vx) / 2
            y = (y + vy) / 2
            pts.append((x, y))
        return pts


# -----------------------------------------
# Voronoi Diagram (naive implementation)
# -----------------------------------------

class VoronoiDiagram:

    def __init__(self, points):
        self.points = points

    def nearest_site(self, px, py):
        best = None
        best_dist = float("inf")
        for sx, sy in self.points:
            dx = px - sx
            dy = py - sy
            d = dx*dx + dy*dy
            if d < best_dist:
                best_dist = d
                best = (sx, sy)
        return best

    def generate_grid(self, width, height):
        grid = []
        for x in range(width):
            for y in range(height):
                site = self.nearest_site(x, y)
                grid.append((x, y, site))
        return grid


# -----------------------------------------
# Laplace-Beltrami Operator (mesh smoothing)
# -----------------------------------------

class Mesh:
    def __init__(self, vertices=None, faces=None):
        self.vertices = vertices or []
        self.faces = faces or []
        self.neighbors = defaultdict(set)

    def build_adjacency(self):
        for f in self.faces:
            a, b, c = f
            self.neighbors[a].update([b, c])
            self.neighbors[b].update([a, c])
            self.neighbors[c].update([a, b])

    def laplace_beltrami_step(self, lam=0.5):
        new_vertices = []

        for i, v in enumerate(self.vertices):
            nbrs = self.neighbors[i]
            if not nbrs:
                new_vertices.append(v)
                continue

            avg_x = avg_y = avg_z = 0.0
            for n in nbrs:
                nv = self.vertices[n]
                avg_x += nv[0]
                avg_y += nv[1]
                avg_z += nv[2]

            count = len(nbrs)
            avg_x /= count
            avg_y /= count
            avg_z /= count

            vx, vy, vz = v
            vx += lam * (avg_x - vx)
            vy += lam * (avg_y - vy)
            vz += lam * (avg_z - vz)

            new_vertices.append((vx, vy, vz))

        self.vertices = new_vertices


# -----------------------------------------
# GPU Batch Simulation (vector batching)
# -----------------------------------------

class GPUBatch:

    def __init__(self):
        self.buffers = []

    def upload(self, data):
        self.buffers.append(data)

    def clear(self):
        self.buffers.clear()

    def draw(self):
        draw_calls = 0
        for buffer in self.buffers:
            draw_calls += 1
        return draw_calls


# -----------------------------------------
# Kernel integration helpers
# -----------------------------------------

def generate_fractal_batch():
    fractal = FractalBatch()
    mandel = fractal.mandelbrot(128, 128)
    sier = fractal.sierpinski(5000)
    return mandel, sier


def compute_voronoi(points, width=128, height=128):
    v = VoronoiDiagram(points)
    return v.generate_grid(width, height)


def smooth_mesh(mesh, steps=5):
    mesh.build_adjacency()
    for _ in range(steps):
        mesh.laplace_beltrami_step()
    return mesh


def gpu_batch_draw(geometry_batches):
    gpu = GPUBatch()
    for g in geometry_batches:
        gpu.upload(g)
    return gpu.draw()


# =========================================
# End of Part 3
# =========================================

import os
import time
import numpy as np
import torch
import cad_master_kernel as cmk

print("\n=== NeuroCAD SMT Ultra :: KERNEL DEMO BUILD ===\n")

# ============================================================
# CONFIG (Tunable like a real engine)
# ============================================================
OUTPUT_DIR = "output_models"
RES = 96
BOUNDS = 2.5

np.random.seed(42)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# STAGE 1 — GEOMETRY GRAPH (SDF)
# ============================================================
class KleinSDF:
    def __call__(self, pts):
        x = pts[:, 0]
        y = pts[:, 1]
        z = pts[:, 2]

        a = 2.0
        r = (x**2 + y**2 + z**2 + a**2 - 2*a*y)
        f = r**2 - 8*a**2*(x**2 + z**2)

        return f

def build_graph():
    print("[Stage 1] Building SDF graph...")
    start = time.time()

    sdf = KleinSDF()

    print("  ✔ Graph ready")
    print("  ⏱ Time:", round(time.time() - start, 4), "s\n")
    return sdf

# ============================================================
# STAGE 2 — FIELD SAMPLING
# ============================================================
def eval_sdf(sdf, pts):
    pts_np = np.array(pts, dtype=np.float32)

    # Custom SDF
    if callable(sdf):
        return sdf(pts_np).astype(np.float32).flatten()

    # Kernel samplers
    try:
        sampler = cmk.FieldSampler(sdf)
        result = sampler.sample(torch.tensor(pts_np))
        return result.detach().cpu().numpy().flatten()
    except:
        pass

    try:
        sampler = cmk.BatchedSDFEvaluator(sdf, device='cpu')
        result = sampler.evaluate(torch.tensor(pts_np))
        return result.detach().cpu().numpy().flatten()
    except:
        pass

    # Fallback
    return np.linalg.norm(pts_np, axis=1) - 1.0

def build_field(sdf):
    print("[Stage 2] Sampling scalar field...")
    start = time.time()

    lin = np.linspace(-BOUNDS, BOUNDS, RES)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    values = eval_sdf(sdf, pts)
    field = values.reshape((RES, RES, RES))

    print("  ✔ Field shape:", field.shape)
    print("  ✔ Min/Max:", float(values.min()), "/", float(values.max()))
    print("  ⏱ Time:", round(time.time() - start, 3), "s\n")

    return field

# ============================================================
# STAGE 3 — MESH EXTRACTION
# ============================================================
def build_mesh(field):
    print("[Stage 3] Extracting mesh (Marching Cubes)...")
    start = time.time()

    mc = cmk.MarchingCubes()
    verts, faces, _ = mc.extract(field, BOUNDS)

    if verts is None or faces is None or len(verts) == 0:
        raise Exception("Mesh extraction failed")

    verts = np.asarray(verts, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.int32)

    print("  ✔ Vertices:", verts.shape)
    print("  ✔ Faces:", faces.shape)
    print("  ✔ Density:", round(len(faces) / len(verts), 2))
    print("  ⏱ Time:", round(time.time() - start, 3), "s\n")

    return {
        "verts": verts,
        "faces": faces
    }

# ============================================================
# STAGE 4 — EXPORT
# ============================================================
def export_stl(mesh_data):
    print("[Stage 4A] Exporting STL...")
    path = os.path.join(OUTPUT_DIR, "klein_bottle.stl")

    try:
        exporter = cmk.MeshExporter()
        exporter.export_stl(mesh_data, path)
        print("  ✔ STL saved:", path)
    except Exception as e:
        print("  ✖ STL export failed:", e)

def export_scad():
    print("[Stage 4B] Exporting SCAD...")

    path = os.path.join(OUTPUT_DIR, "klein_bottle.scad")

    scad_code = f"""
// === Klein Bottle (Engine Export) ===
$fn = {RES};

module klein() {{
    for (u = [0:10:360]) {{
        for (v = [0:10:360]) {{

            x = (2 + cos(v)) * cos(u);
            y = (2 + cos(v)) * sin(u);
            z = sin(v);

            translate([x, y, z])
                sphere(r = 0.08);
        }}
    }}
}}

scale([0.4,0.4,0.4])
    klein();
"""

    with open(path, "w") as f:
        f.write(scad_code)

    print("  ✔ SCAD saved:", path)

# ============================================================
# MAIN PIPELINE
# ============================================================
if __name__ == "__main__":
    total_start = time.time()

    sdf = build_graph()
    field = build_field(sdf)
    mesh = build_mesh(field)

    export_stl(mesh)
    export_scad()

    print("\n=== PIPELINE COMPLETE ===")
    print("Total Time:", round(time.time() - total_start, 3), "s\n")

    # ----------------------------
# Kernel Logger
# ----------------------------
class KernelLogger:
    def __init__(self):
        self.logs = []

    def log(self, msg):
        print(msg)
        self.logs.append(msg)

LOGGER = KernelLogger()


# ----------------------------
# Kernel Profiler
# ----------------------------
class KernelProfiler:
    def __init__(self):
        self.times = {}

    def start(self, name):
        self.times[name] = -time.time()

    def stop(self, name):
        self.times[name] += time.time()

    def report(self):
        print("\n[Profiler Report]")
        for k, v in self.times.items():
            print(f"  {k}: {round(v, 4)} s")

PROFILER = KernelProfiler()

class KernelContext:
    def __init__(self):
        self.cache = {}
        self.nodes = []
        self.device = "cpu"

    def register(self, node):
        self.nodes.append(node)

CTX = KernelContext()

class KernelContext:
    def __init__(self):
        self.cache = {}
        self.nodes = []
        self.device = "cpu"

    def register(self, node):
        self.nodes.append(node)

CTX = KernelContext()

class KernelPlugin:
    def __init__(self, name):
        self.name = name

    def register(self):
        pass


PLUGINS = {}

def register_plugin(plugin):
    PLUGINS[plugin.name] = plugin
    plugin.register()

    class KernelPlugin:
    def __init__(self, name):
        self.name = name

    def register(self):
        pass


PLUGINS = {}

def register_plugin(plugin):
    PLUGINS[plugin.name] = plugin
    plugin.register()
    def optimize_sdf_tree(node):
    LOGGER.log("[Optimizer] Simplifying SDF tree...")

    # Example: collapse nested unions
    if hasattr(node, "inputs") and len(node.inputs) == 2:
        a, b = node.inputs

        if node.op == op_union and hasattr(a, "op") and a.op == op_union:
            LOGGER.log("  ✔ Flattening union tree")

    return node

    class Param:
    def __init__(self, name, value, min_val=None, max_val=None):
        self.name = name
        self.value = value
        self.min = min_val
        self.max = max_val


PARAMS = {}

def register_param(name, value, min_val=None, max_val=None):
    PARAMS[name] = Param(name, value, min_val, max_val)

def get_param(name):
    return PARAMS[name].value
class Param:
    def __init__(self, name, value, min_val=None, max_val=None):
        self.name = name
        self.value = value
        self.min = min_val
        self.max = max_val


PARAMS = {}

def register_param(name, value, min_val=None, max_val=None):
    PARAMS[name] = Param(name, value, min_val, max_val)

def get_param(name):
    return PARAMS[name].value

    def build_advanced_graph():
    LOGGER.log("[Stage X+] Building Advanced Graph...")

    register_param("blend_k", 0.3, 0.0, 1.0)

    def klein(pts):
        x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
        a = 2.0
        r = (x**2 + y**2 + z**2 + a**2 - 2*a*y)
        return r**2 - 8*a**2*(x**2 + z**2)

    def sphere(pts):
        return np.linalg.norm(pts, axis=1) - 0.8

    sdf = op_smooth_sub(klein, sphere, k=get_param("blend_k"))

    return sdf
class Backend:
    def __init__(self, mode="cpu"):
        self.mode = mode

    def tensor(self, x):
        if self.mode == "gpu":
            return torch.tensor(x, dtype=torch.float32).cuda()
        return torch.tensor(x, dtype=torch.float32)

BACKEND = Backend(mode="cpu")  # switch to "gpu" laterclass Backend:
    def __init__(self, mode="cpu"):
        self.mode = mode

    def tensor(self, x):
        if self.mode == "gpu":
            return torch.tensor(x, dtype=torch.float32).cuda()
        return torch.tensor(x, dtype=torch.float32)

BACKEND = Backend(mode="cpu")  # switch to "gpu" later

def parallel_field(sdf, res):
    LOGGER.log("[Parallel Field] Sampling...")

    lin = np.linspace(-BOUNDS, BOUNDS, res)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    # Split into chunks
    chunks = np.array_split(pts, 8)

    futures = [JOBS.run(sdf, c) for c in chunks]
    results = [f.result() for f in futures]

    values = np.concatenate(results)
    return values.reshape((res, res, res))
    def parallel_field(sdf, res):
    LOGGER.log("[Parallel Field] Sampling...")

    lin = np.linspace(-BOUNDS, BOUNDS, res)
    X, Y, Z = np.meshgrid(lin, lin, lin, indexing="ij")
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)

    # Split into chunks
    chunks = np.array_split(pts, 8)

    futures = [JOBS.run(sdf, c) for c in chunks]
    results = [f.result() for f in futures]

    values = np.concatenate(results)
    return values.reshape((res, res, res))
def engine_loop(iterations=3):
    LOGGER.log("\n[Engine] Starting live loop...\n")

    sdf = build_advanced_graph()

    for i in range(iterations):
        LOGGER.log(f"[Frame {i}]")

        # Simulate parameter animation
        if "blend_k" in PARAMS:
            PARAMS["blend_k"].value = 0.2 + 0.1 * np.sin(i)

        field = parallel_field(sdf, RES)

        mesh = build_mesh(field)
        mesh = analyze_mesh(mesh)

        LOGGER.log("  ✔ Frame complete\n")

    LOGGER.log("[Engine] Loop finished\n")

