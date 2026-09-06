# vector_field_engine.py

import numpy as np


class VectorFieldEngine:
    @staticmethod
    def _grid_size(value):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("grid_size must be a positive integer")
        return value

    # --------------------------------
    # Generic 3D Vector Field
    # --------------------------------

    def create_uniform_field(self, direction, magnitude, grid_size=20):
        grid_size = self._grid_size(grid_size)
        dir_vec = np.asarray(direction, dtype=float)
        if dir_vec.shape != (3,) or not np.all(np.isfinite(dir_vec)):
            raise ValueError("direction must contain three finite values")
        norm = float(np.linalg.norm(dir_vec))
        if norm == 0:
            raise ValueError("direction cannot be the zero vector")
        if not isinstance(magnitude, (int, float)) or isinstance(magnitude, bool) or not np.isfinite(magnitude):
            raise ValueError("magnitude must be finite")
        vector = dir_vec / norm * float(magnitude)
        return np.broadcast_to(vector, (grid_size, grid_size, grid_size, 3)).copy()

    # --------------------------------
    # Vortex Field
    # --------------------------------

    def create_vortex_field(self, grid_size=20, strength=1.0):
        grid_size = self._grid_size(grid_size)
        if not isinstance(strength, (int, float)) or isinstance(strength, bool) or not np.isfinite(strength):
            raise ValueError("strength must be finite")
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
        vertices = np.asarray(vertices, dtype=float)
        field = np.asarray(field, dtype=float)
        if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.all(np.isfinite(vertices)):
            raise ValueError("vertices must be a finite N×3 array")
        if field.ndim != 4 or field.shape[-1] != 3 or len(set(field.shape[:3])) != 1 or not np.all(np.isfinite(field)):
            raise ValueError("field must be a finite cubic N×N×N×3 array")
        if not isinstance(influence, (int, float)) or isinstance(influence, bool) or not np.isfinite(influence):
            raise ValueError("influence must be finite")
        deformed = []

        grid_size = field.shape[0]

        for v in vertices:
            x = int(abs(v[0]) % grid_size)
            y = int(abs(v[1]) % grid_size)
            z = int(abs(v[2]) % grid_size)

            force = field[x, y, z]
            deformed.append(v + force * influence)

        return np.asarray(deformed)

    # --------------------------------
    # Stress Visualization
    # --------------------------------

    def compute_gradient_field(self, scalar_field):
        scalar_field = np.asarray(scalar_field, dtype=float)
        if scalar_field.ndim != 3 or min(scalar_field.shape) < 2 or not np.all(np.isfinite(scalar_field)):
            raise ValueError("scalar_field must be a finite 3D array with at least two samples per axis")
        grad = np.gradient(scalar_field)
        return np.stack(grad, axis=-1)
