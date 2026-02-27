# vector_field_engine.py

import numpy as np


class VectorFieldEngine:

    def __init__(self):
        pass

    # --------------------------------
    # Generic 3D Vector Field
    # --------------------------------

    def create_uniform_field(self, direction, magnitude, grid_size=20):
        field = np.zeros((grid_size, grid_size, grid_size, 3))

        dir_vec = np.array(direction)
        dir_vec = dir_vec / np.linalg.norm(dir_vec)

        for i in range(grid_size):
            for j in range(grid_size):
                for k in range(grid_size):
                    field[i, j, k] = dir_vec * magnitude

        return field

    # --------------------------------
    # Vortex Field
    # --------------------------------

    def create_vortex_field(self, grid_size=20, strength=1.0):
        field = np.zeros((grid_size, grid_size, grid_size, 3))
        center = grid_size // 2

        for i in range(grid_size):
            for j in range(grid_size):
                x = i - center
                y = j - center

                r = np.sqrt(x**2 + y**2) + 1e-6
                vx = -y / r * strength
                vy = x / r * strength

                for k in range(grid_size):
                    field[i, j, k] = [vx, vy, 0]

        return field

    # --------------------------------
    # Apply Field to Mesh
    # --------------------------------

    def deform_mesh(self, vertices, field, influence=0.01):
        deformed = []

        grid_size = field.shape[0]

        for v in vertices:
            x = int(abs(v[0]) % grid_size)
            y = int(abs(v[1]) % grid_size)
            z = int(abs(v[2]) % grid_size)

            force = field[x, y, z]
            deformed.append(v + force * influence)

        return np.array(deformed)

    # --------------------------------
    # Stress Visualization
    # --------------------------------

    def compute_gradient_field(self, scalar_field):
        grad = np.gradient(scalar_field)
        return np.stack(grad, axis=-1)
