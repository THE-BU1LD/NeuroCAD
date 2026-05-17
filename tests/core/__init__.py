"""Compatibility shim so test scripts executed from tests/ can import core.*"""
from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
__path__ = [os.path.join(_ROOT, "core")]
