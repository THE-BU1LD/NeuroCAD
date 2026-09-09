"""Honest capability models shared by NeuroCAD application adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CapabilityState(str, Enum):
    """How far an integration operation is actually implemented."""

    NATIVE = "native"
    AVAILABLE = "available"
    VERIFIED = "verified"
    FILE_EXCHANGE = "file_exchange"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Prerequisite:
    id: str
    available: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "available": self.available, "detail": self.detail}


@dataclass(frozen=True)
class Capability:
    operation: str
    state: CapabilityState
    formats: tuple[str, ...]
    detail: str
    external_operation_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "state": self.state.value,
            "formats": list(self.formats),
            "detail": self.detail,
            "external_operation_performed": self.external_operation_performed,
        }


@dataclass(frozen=True)
class ApplicationAdapter:
    id: str
    display_name: str
    capabilities: tuple[Capability, ...]
    prerequisites: tuple[Prerequisite, ...] = ()
    limitations: tuple[str, ...] = ()

    def capability(self, operation: str) -> Capability:
        for capability in self.capabilities:
            if capability.operation == operation:
                return capability
        raise KeyError(f"{self.id!r} has no declared capability {operation!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "capabilities": [capability.to_dict() for capability in self.capabilities],
            "prerequisites": [prerequisite.to_dict() for prerequisite in self.prerequisites],
            "limitations": list(self.limitations),
        }


class IntegrationUnavailableError(RuntimeError):
    """Raised when a caller requests an operation whose gate is unavailable."""
