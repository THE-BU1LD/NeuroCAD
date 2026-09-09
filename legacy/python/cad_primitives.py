PRIMITIVE_REGISTRY = {}

def register(name):
    def wrapper(fn):
        PRIMITIVE_REGISTRY[name] = fn
        return fn
    return wrapper