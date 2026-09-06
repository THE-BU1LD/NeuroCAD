from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Component:
    """A design component with a name, geometric parameters, and placement."""

    name: str
    params: dict[str, Any]
    operation: str = "union"  # union | difference | intersection
    transform: dict[str, Sequence[float]] = field(
        default_factory=lambda: {
            "translate": (0.0, 0.0, 0.0),
            "rotate": (0.0, 0.0, 0.0),
            "scale": (1.0, 1.0, 1.0),
        }
    )
    role: str = "body"

    def geometry(self) -> dict[str, Any]:
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
        self.components: list[Component] = []
        self.connections: list[Connection] = []
        self.metadata: dict[str, Any] = {}

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

    def as_pairs(self) -> list[tuple[Component, Component]]:
        return [(c.a, c.b) for c in self.connections]

    def summary(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "component_count": len(self.components),
            "connection_count": len(self.connections),
            "metadata": dict(self.metadata),
        }
