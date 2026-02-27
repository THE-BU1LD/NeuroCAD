# parts.py
class Part:
    def __init__(self, name, mass, centroid, material="steel"):
        self.name = name
        self.mass = mass
        self.centroid = centroid
        self.material = material

    def inertia_proxy(self):
        return self.mass * sum(c * c for c in self.centroid)
