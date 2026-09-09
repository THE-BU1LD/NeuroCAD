"""UTF-8 source/JSON reads must not depend on Windows' active code page."""

import ast
from pathlib import Path


def test_maintained_text_reads_declare_an_encoding() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = [path for name in ("core", "scripts", "tests") for path in (root / name).rglob("*.py")]
    sources.extend(root.glob("*.py"))
    assert sources
    missing = []
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr == "read_text" and not node.args and not any(key.arg == "encoding" for key in node.keywords):
                missing.append(f"{source.relative_to(root)}:{node.lineno}")
    assert not missing, f"Use explicit UTF-8 instead of the host code page: {missing}"
