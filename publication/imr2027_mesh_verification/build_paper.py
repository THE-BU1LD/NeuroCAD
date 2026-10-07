#!/usr/bin/env python3
"""Compile the prepared research note with the supplied prior official SIAM style."""
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
executable = shutil.which('pdflatex')
if executable is None:
    raise SystemExit('Install a TeX distribution first.')
for _ in range(2):
    subprocess.run([str(Path(executable).absolute()), '-halt-on-error', '-interaction=nonstopmode', '-no-shell-escape', 'research_note.tex'], cwd=root, check=True, timeout=120)
