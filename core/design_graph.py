class Component:
    def __init__(self, name, params):
        self.name = name
        self.params = params

class Connection:
    def __init__(self, a, b, relation):
        self.a = a
        self.b = b
        self.relation = relation

class DesignGraph:
    def __init__(self):
        self.components = []
        self.connections = []

    def add_component(self, c):
        self.components.append(c)

    def connect(self, a, b, relation):
        self.connections.append(Connection(a, b, relation))
