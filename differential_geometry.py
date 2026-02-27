import numpy as np


# ============================================
# GRADIENT + HESSIAN
# ============================================

class DifferentialOperators:

    def gradient(self, sdf, p, eps=1e-4):
        g = np.zeros(p.shape)
        for i in range(3):
            d = np.zeros(3)
            d[i] = eps
            g[..., i] = (
                sdf(p + d) - sdf(p - d)
            ) / (2 * eps)
        return g


# ============================================
# SMOOTH BOOLEAN
# ============================================

class SmoothBoolean:

    def smooth_union(self, a, b, k=0.3):
        h = np.clip(0.5 + 0.5*(b-a)/k, 0, 1)
        return a*(1-h) + b*h - k*h*(1-h)

    def smooth_subtraction(self, a, b, k=0.3):
        return -self.smooth_union(-a, b, k)

    def smooth_intersection(self, a, b, k=0.3):
        return self.smooth_union(a, b, k)


# ============================================
# DEFORMATION
# ============================================

class DeformationField:

    def twist(self, p, strength=1.0):
        x, y, z = p[...,0], p[...,1], p[...,2]
        theta = strength * z
        ct = np.cos(theta)
        st = np.sin(theta)
        x2 = ct*x - st*y
        y2 = st*x + ct*y
        return np.stack([x2, y2, z], axis=-1)

    def bend(self, p, k=0.3):
        x, y, z = p[...,0], p[...,1], p[...,2]
        r = 1/k
        theta = x*k
        cx = r*np.sin(theta)
        cz = r*(1-np.cos(theta))
        return np.stack([cx, y, z+cz], axis=-1)
