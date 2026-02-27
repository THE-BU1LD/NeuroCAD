class Primitive:
    def __init__(self, kind, dims):
        self.kind = kind
        self.dims = dims

def box(w, h, d):
    return Primitive("box", dict(w=w, h=h, d=d))

def cylinder(r, h):
    return Primitive("cylinder", dict(r=r, h=h))
