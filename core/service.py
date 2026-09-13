"""User-level service definitions for the NeuroCAD daemon."""

from __future__ import annotations

import os
import platform
import plistlib
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

from .artifacts import write_text_atomic
from .config import NeuroCADConfig

SERVICE_LABEL = "com.thebu1ld.neurocad"


def service_command(config_path: Path) -> list[str]:
    return [sys.executable, "-m", "core.daemon", "serve", "--config", str(config_path)]


def install_user_service(config_path: Path, config: NeuroCADConfig, *, activate: bool = True) -> dict[str, Any]:
    system = platform.system()
    command = service_command(config_path)
    if system == "Darwin":
        destination = Path(
            os.environ.get(
                "NEUROCAD_LAUNCH_AGENTS_DIR",
                Path.home() / "Library" / "LaunchAgents",
            )
        ).expanduser() / f"{SERVICE_LABEL}.plist"
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "Label": SERVICE_LABEL,
            "ProgramArguments": command,
            "RunAtLoad": True,
            "KeepAlive": {"SuccessfulExit": False},
            "ProcessType": "Background",
            "StandardOutPath": config.log_path,
            "StandardErrorPath": config.log_path,
        }
        temporary = destination.with_suffix(".plist.tmp")
        temporary.write_bytes(plistlib.dumps(payload, sort_keys=True))
        os.replace(temporary, destination)
        activated = False
        detail = "service definition installed"
        if activate:
            domain = f"gui/{os.getuid()}"
            subprocess.run(  # nosec B603 B607
                ["launchctl", "bootout", f"{domain}/{SERVICE_LABEL}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            completed = subprocess.run(  # nosec B603 B607
                ["launchctl", "bootstrap", domain, str(destination)],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            activated = completed.returncode == 0
            detail = "service installed and activated" if activated else (completed.stderr or completed.stdout).strip()
        return {"manager": "launchd", "path": str(destination), "activated": activated, "detail": detail}
    if system == "Linux":
        destination = Path(
            os.environ.get(
                "NEUROCAD_SYSTEMD_USER_DIR",
                Path.home() / ".config" / "systemd" / "user",
            )
        ).expanduser() / "neurocad.service"
        destination.parent.mkdir(parents=True, exist_ok=True)
        quoted = " ".join(_systemd_quote(part) for part in command)
        unit = "\n".join(
            [
                "[Unit]",
                "Description=NeuroCAD local generation daemon",
                "",
                "[Service]",
                f"ExecStart={quoted}",
                "Restart=on-failure",
                "RestartSec=2",
                "",
                "[Install]",
                "WantedBy=default.target",
                "",
            ]
        )
        write_text_atomic(destination, unit)
        activated = False
        detail = "service definition installed"
        if activate:
            reload_result = subprocess.run(  # nosec B603 B607
                ["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True, timeout=20
            )
            if reload_result.returncode == 0:
                completed = subprocess.run(  # nosec B603 B607
                    ["systemctl", "--user", "enable", "--now", "neurocad.service"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                activated = completed.returncode == 0
                detail = "service installed and activated" if activated else (completed.stderr or completed.stdout).strip()
            else:
                detail = (reload_result.stderr or reload_result.stdout).strip()
        return {"manager": "systemd-user", "path": str(destination), "activated": activated, "detail": detail}
    return {"manager": "direct", "path": None, "activated": False, "detail": f"no service manager for {system}"}


def _systemd_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def uninstall_user_service(*, remove_definition: bool = True) -> dict[str, Any]:
    """Stop NeuroCAD's user service and optionally remove only its owned definition."""

    system = platform.system()
    if system == "Darwin":
        destination = Path(
            os.environ.get("NEUROCAD_LAUNCH_AGENTS_DIR", Path.home() / "Library" / "LaunchAgents")
        ).expanduser() / f"{SERVICE_LABEL}.plist"
        domain = f"gui/{os.getuid()}"
        completed = subprocess.run(  # nosec B603 B607
            ["launchctl", "bootout", f"{domain}/{SERVICE_LABEL}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        stopped = completed.returncode == 0 or not destination.exists()
        if remove_definition:
            destination.unlink(missing_ok=True)
        return {"manager": "launchd", "path": str(destination), "stopped": stopped, "removed": remove_definition}
    if system == "Linux":
        destination = Path(
            os.environ.get("NEUROCAD_SYSTEMD_USER_DIR", Path.home() / ".config" / "systemd" / "user")
        ).expanduser() / "neurocad.service"
        completed = subprocess.run(  # nosec B603 B607
            ["systemctl", "--user", "disable", "--now", "neurocad.service"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        stopped = completed.returncode == 0 or not destination.exists()
        if remove_definition:
            destination.unlink(missing_ok=True)
            subprocess.run(  # nosec B603 B607
                ["systemctl", "--user", "daemon-reload"], check=False, capture_output=True, text=True, timeout=20
            )
        return {"manager": "systemd-user", "path": str(destination), "stopped": stopped, "removed": remove_definition}
    return {"manager": "direct", "path": None, "stopped": False, "removed": False}
