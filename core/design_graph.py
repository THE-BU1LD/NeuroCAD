from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


@dataclass
class Component:
    """A design component with a name, geometric parameters, and placement."""

    name: str
    params: Dict[str, Any]
    operation: str = "union"  # union | difference | intersection
    transform: Dict[str, Sequence[float]] = field(
        default_factory=lambda: {
            "translate": (0.0, 0.0, 0.0),
            "rotate": (0.0, 0.0, 0.0),
            "scale": (1.0, 1.0, 1.0),
        }
    )
    role: str = "body"

    def geometry(self) -> Dict[str, Any]:
        return self.params.get("geometry", {})


@dataclass
class Connection:
    a: Component
    b: Component
    relation: str = "attached"

    def __iter__(self) -> Iterator[Component]:
        yield self.a
        yield self.b


class DesignGraph:
    def __init__(self, title: str = "design"):
        self.title = title
        self.components: List[Component] = []
        self.connections: List[Connection] = []
        self.metadata: Dict[str, Any] = {}

    def add_component(self, component: Component) -> Component:
        self.components.append(component)
        return component

    def connect(self, a: Component, b: Component, relation: str = "attached") -> Connection:
        conn = Connection(a=a, b=b, relation=relation)
        self.connections.append(conn)
        return conn

    def __iter__(self) -> Iterator[Component]:
        return iter(self.components)

    def __len__(self) -> int:
        return len(self.components)

    def as_pairs(self) -> List[Tuple[Component, Component]]:
        return [(c.a, c.b) for c in self.connections]

    def summary(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "component_count": len(self.components),
            "connection_count": len(self.connections),
            "metadata": dict(self.metadata),
        }
