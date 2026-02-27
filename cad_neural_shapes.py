import numpy as np


class NeuralShapes:
    """
    Procedural neural-style implicit shapes.
    """

    @staticmethod
    def gyroid(p, scale=6.0):
        x, y, z = p * scale
        return (
            np.sin(x) * np.cos(y)
            + np.sin(y) * np.cos(z)
            + np.sin(z) * np.cos(x)
        )

    @staticmethod
    def fractal_noise(p, octaves=4):
        val = 0
        freq = 1.0
        amp = 1.0

        for _ in range(octaves):
            val += amp * np.sin(freq * p[0] + freq * p[1] + freq * p[2])
            freq *= 2.0
            amp *= 0.5

        return val

    @staticmethod
    def complex_combo(p):
        g = NeuralShapes.gyroid(p, 8.0)
        n = NeuralShapes.fractal_noise(p, 5)
        sphere = np.linalg.norm(p) - 0.6
        return g + 0.3 * n + sphere