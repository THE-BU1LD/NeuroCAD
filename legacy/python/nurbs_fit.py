import numpy as np
from scipy.interpolate import bisplrep


class ImplicitToNURBS:

    def fit_patch(self, verts):
        x = verts[:,0]
        y = verts[:,1]
        z = verts[:,2]
        return bisplrep(x, y, z, s=0.01)
