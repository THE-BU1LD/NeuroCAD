import subprocess
import shutil
import os
from typing import Optional


class CADExporter:
    """
    Production-grade CAD exporter.
    """

    def __init__(self, openscad_path: Optional[str] = None):
        self.openscad = openscad_path or shutil.which("openscad")
        if not self.openscad:
            raise RuntimeError("OpenSCAD CLI not found")

    def export_stl(self, scad_path: str, stl_path: str):
        if not os.path.isfile(scad_path):
            raise FileNotFoundError(scad_path)

        cmd = [self.openscad, "-o", stl_path, scad_path]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"OpenSCAD failed:\n{proc.stderr.strip()}"
            )

        return stl_path