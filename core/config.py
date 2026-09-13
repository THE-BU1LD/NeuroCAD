"""Strict user-scoped configuration for terminal-first NeuroCAD."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .json_io import read_bounded_utf8, strict_json_loads

CONFIG_VERSION = "neurocad-config-v1"
MAX_CONFIG_BYTES = 65_536


def _base_paths() -> tuple[Path, Path, Path]:
    user_home = Path.home()
    config_root = Path(os.environ.get("NEUROCAD_CONFIG_DIR", user_home / ".config" / "neurocad"))
    data_root = Path(os.environ.get("NEUROCAD_DATA_DIR", user_home / ".local" / "share" / "neurocad"))
    state_root = Path(os.environ.get("NEUROCAD_STATE_DIR", user_home / ".local" / "state" / "neurocad"))
    return config_root.expanduser(), data_root.expanduser(), state_root.expanduser()


def default_config_path() -> Path:
    return _base_paths()[0] / "config.json"


@dataclass(frozen=True)
class NeuroCADConfig:
    version: str
    data_root: str
    state_root: str
    output_root: str
    socket_path: str
    log_path: str
    worker_count: int = 1
    default_fn: int = 64
    default_timeout_seconds: int = 120
    default_formats: tuple[str, ...] = ("ir", "scad", "stl", "preview")

    @classmethod
    def defaults(cls) -> NeuroCADConfig:
        _, data_root, state_root = _base_paths()
        return cls(
            version=CONFIG_VERSION,
            data_root=str(data_root),
            state_root=str(state_root),
            output_root=str(data_root / "outputs"),
            socket_path=str(state_root / "neurocad.sock"),
            log_path=str(state_root / "daemon.log"),
        )

    def validate(self) -> None:
        if self.version != CONFIG_VERSION:
            raise ValueError(f"config version must be {CONFIG_VERSION!r}")
        for field in ("data_root", "state_root", "output_root", "socket_path", "log_path"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise TypeError(f"config field {field!r} must be a non-empty string")
            path = Path(value).expanduser()
            if not path.is_absolute():
                raise ValueError(f"config field {field!r} must be an absolute path")
        if isinstance(self.worker_count, bool) or not isinstance(self.worker_count, int) or not 1 <= self.worker_count <= 8:
            raise ValueError("worker_count must be an integer from 1 through 8")
        if isinstance(self.default_fn, bool) or not isinstance(self.default_fn, int) or not 3 <= self.default_fn <= 1000:
            raise ValueError("default_fn must be an integer from 3 through 1000")
        if (
            isinstance(self.default_timeout_seconds, bool)
            or not isinstance(self.default_timeout_seconds, int)
            or not 1 <= self.default_timeout_seconds <= 3600
        ):
            raise ValueError("default_timeout_seconds must be an integer from 1 through 3600")
        allowed = {"ir", "scad", "stl", "preview"}
        if not self.default_formats or len(self.default_formats) != len(set(self.default_formats)):
            raise ValueError("default_formats must be a non-empty list without duplicates")
        if set(self.default_formats) - allowed:
            raise ValueError(f"default_formats contains unsupported values: {sorted(set(self.default_formats) - allowed)}")
        state_root = Path(self.state_root).resolve()
        socket_path = Path(self.socket_path).resolve()
        log_path = Path(self.log_path).resolve()
        if state_root not in socket_path.parents or state_root not in log_path.parents:
            raise ValueError("socket_path and log_path must remain below state_root")
        if len(os.fsencode(socket_path)) > 100:
            raise ValueError("socket_path is too long for a portable Unix-domain socket (maximum 100 encoded bytes)")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["default_formats"] = list(self.default_formats)
        return value


def load_config(path: Path | None = None, *, require_exists: bool = False) -> NeuroCADConfig:
    path = (path or default_config_path()).expanduser().resolve()
    if not path.exists():
        if require_exists:
            raise FileNotFoundError(f"NeuroCAD is not configured; run 'neurocad setup' ({path})")
        config = NeuroCADConfig.defaults()
        config.validate()
        return config
    value = strict_json_loads(read_bounded_utf8(path, max_bytes=MAX_CONFIG_BYTES, label="NeuroCAD config"))
    if not isinstance(value, dict):
        raise TypeError("NeuroCAD config must be a JSON object")
    allowed = set(NeuroCADConfig.__dataclass_fields__)
    unknown = set(value) - allowed
    missing = allowed - set(value)
    if unknown:
        raise ValueError(f"NeuroCAD config has unknown fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"NeuroCAD config is missing fields: {sorted(missing)}")
    formats = value.get("default_formats")
    if not isinstance(formats, list) or any(not isinstance(item, str) for item in formats):
        raise TypeError("default_formats must be a list of strings")
    value["default_formats"] = tuple(formats)
    config = NeuroCADConfig(**value)
    config.validate()
    return config


def write_config(config: NeuroCADConfig, path: Path | None = None, *, overwrite: bool = False) -> Path:
    config.validate()
    destination = (path or default_config_path()).expanduser().resolve()
    if destination.exists() and not overwrite:
        raise FileExistsError(f"config already exists: {destination}")
    return write_text_atomic(destination, json.dumps(config.to_dict(), indent=2, sort_keys=True) + "\n")


def load_or_create_config(path: Path | None = None) -> tuple[NeuroCADConfig, Path, bool]:
    """Load strict user configuration, creating safe defaults on first use."""

    destination = (path or default_config_path()).expanduser().resolve()
    if destination.exists():
        return load_config(destination, require_exists=True), destination, False
    config = NeuroCADConfig.defaults()
    write_config(config, destination)
    return config, destination, True


def ensure_runtime_directories(config: NeuroCADConfig) -> None:
    config.validate()
    for path in (Path(config.data_root), Path(config.state_root), Path(config.output_root), Path(config.log_path).parent):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
