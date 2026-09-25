"""Exact-CAD backend discovery and capability contracts.

The verified NeuroCAD v1 compiler does not depend on any exact-CAD package.
Backends here are optional and are discovered without importing heavy kernels.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict, dataclass
from importlib import metadata
from typing import Callable

EXACT_BACKEND_API_VERSION = "neurocad-exact-backend-v1"


class ExactBackendUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ExactBackendDescriptor:
    id: str
    display_name: str
    module: str
    distribution: str
    minimum_python: tuple[int, int]
    formats: tuple[str, ...]
    capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "module": self.module,
            "distribution": self.distribution,
            "minimum_python": list(self.minimum_python),
            "formats": list(self.formats),
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True)
class ExactBackendStatus:
    descriptor: ExactBackendDescriptor
    available: bool
    reason: str
    installed_version: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "api_version": EXACT_BACKEND_API_VERSION,
            "backend": self.descriptor.to_dict(),
            "available": self.available,
            "reason": self.reason,
            "installed_version": self.installed_version,
        }


BACKENDS = (
    ExactBackendDescriptor(
        id="build123d",
        display_name="build123d / OpenCascade",
        module="build123d",
        distribution="build123d",
        minimum_python=(3, 11),
        formats=("step", "stl", "brep"),
        capabilities=(
            "feature_history_compile",
            "brep_build",
            "step_export",
            "stl_export",
            "geometric_inspection",
        ),
    ),
    ExactBackendDescriptor(
        id="cadquery",
        display_name="CadQuery / OpenCascade",
        module="cadquery",
        distribution="cadquery",
        minimum_python=(3, 11),
        formats=("step", "stl"),
        capabilities=(
            "feature_history_compile",
            "brep_build",
            "step_export",
            "stl_export",
            "assembly_export",
            "geometric_inspection",
        ),
    ),
)


def _default_module_finder(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _default_version_reader(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def discover_exact_backends(
    *,
    python_version: tuple[int, int] | None = None,
    module_finder: Callable[[str], bool] | None = None,
    version_reader: Callable[[str], str | None] | None = None,
) -> tuple[ExactBackendStatus, ...]:
    runtime = python_version or (sys.version_info.major, sys.version_info.minor)
    find_module = module_finder or _default_module_finder
    read_version = version_reader or _default_version_reader
    statuses: list[ExactBackendStatus] = []
    for descriptor in BACKENDS:
        if runtime < descriptor.minimum_python:
            statuses.append(
                ExactBackendStatus(
                    descriptor=descriptor,
                    available=False,
                    reason=(
                        f"requires Python {descriptor.minimum_python[0]}.{descriptor.minimum_python[1]}+; "
                        f"runtime is {runtime[0]}.{runtime[1]}"
                    ),
                    installed_version=None,
                )
            )
            continue
        if not find_module(descriptor.module):
            statuses.append(
                ExactBackendStatus(
                    descriptor=descriptor,
                    available=False,
                    reason=f"Python module {descriptor.module!r} is not installed",
                    installed_version=None,
                )
            )
            continue
        version = read_version(descriptor.distribution)
        statuses.append(
            ExactBackendStatus(
                descriptor=descriptor,
                available=True,
                reason="optional exact-CAD backend detected; no geometry has been built by discovery",
                installed_version=version,
            )
        )
    return tuple(statuses)


def exact_backend_status(identifier: str, **kwargs: object) -> ExactBackendStatus:
    normalized = identifier.strip().lower()
    for status in discover_exact_backends(**kwargs):
        if status.descriptor.id == normalized:
            return status
    choices = ", ".join(item.id for item in BACKENDS)
    raise KeyError(f"unknown exact-CAD backend {identifier!r}; choose one of {choices}")


def require_exact_backend(identifier: str, **kwargs: object) -> ExactBackendStatus:
    status = exact_backend_status(identifier, **kwargs)
    if not status.available:
        raise ExactBackendUnavailable(f"{status.descriptor.display_name} unavailable: {status.reason}")
    return status
