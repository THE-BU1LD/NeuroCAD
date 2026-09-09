import numpy as np


class TextureLibrary:

    @staticmethod
    def checker(uv, scale=10):
        uv = uv * scale
        checks = ((uv[:, 0].astype(int) + uv[:, 1].astype(int)) % 2)
        return np.stack([checks, checks, checks], axis=1)

    @staticmethod
    def stripes(uv, scale=10):
        s = (uv[:, 0] * scale).astype(int) % 2
        return np.stack([s, 1 - s, 0.5 * np.ones_like(s)], axis=1)