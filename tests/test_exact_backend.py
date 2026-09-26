from __future__ import annotations

import pytest

from core.exact_backend import (
    ExactBackendUnavailable,
    discover_exact_backends,
    exact_backend_status,
    require_exact_backend,
)


def test_exact_backend_discovery_fails_closed_on_python_310() -> None:
    statuses = discover_exact_backends(
        python_version=(3, 10),
        module_finder=lambda _: True,
        version_reader=lambda _: "999",
    )
    assert statuses
    assert all(not status.available for status in statuses)
    assert all("requires Python 3.11+" in status.reason for status in statuses)


def test_exact_backend_discovery_reports_missing_optional_modules() -> None:
    statuses = discover_exact_backends(
        python_version=(3, 11),
        module_finder=lambda _: False,
        version_reader=lambda _: None,
    )
    assert {status.descriptor.id for status in statuses} == {"build123d", "cadquery"}
    assert all(not status.available for status in statuses)
    assert all("not installed" in status.reason for status in statuses)


def test_exact_backend_discovery_reports_versions_without_building_geometry() -> None:
    versions = {"build123d": "0.13.0", "cadquery": "2.8.0"}
    statuses = discover_exact_backends(
        python_version=(3, 12),
        module_finder=lambda _: True,
        version_reader=lambda distribution: versions[distribution],
    )
    assert all(status.available for status in statuses)
    assert {status.descriptor.id: status.installed_version for status in statuses} == versions
    assert all("no geometry has been built" in status.reason for status in statuses)


def test_require_exact_backend_rejects_unavailable_backend() -> None:
    with pytest.raises(ExactBackendUnavailable, match="unavailable"):
        require_exact_backend(
            "build123d",
            python_version=(3, 12),
            module_finder=lambda _: False,
            version_reader=lambda _: None,
        )


def test_exact_backend_status_rejects_unknown_backend() -> None:
    with pytest.raises(KeyError, match="unknown exact-CAD backend"):
        exact_backend_status(
            "invented",
            python_version=(3, 12),
            module_finder=lambda _: False,
            version_reader=lambda _: None,
        )


def test_exact_backend_status_is_json_ready() -> None:
    status = exact_backend_status(
        "build123d",
        python_version=(3, 12),
        module_finder=lambda _: True,
        version_reader=lambda _: "0.13.0",
    )
    payload = status.to_dict()
    assert payload["api_version"] == "neurocad-exact-backend-v1"
    assert payload["available"] is True
    assert payload["installed_version"] == "0.13.0"
    assert payload["backend"]["formats"] == ["step", "stl", "brep"]
