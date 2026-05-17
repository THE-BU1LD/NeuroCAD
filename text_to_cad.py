from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.prompt_engine import generate_design
from core.scad_export import design_to_scad


@dataclass
class TextCADDocument:
    prompt: str
    design: object
    scad: str


class TextToCAD:
    def __init__(self, output_path: Optional[str] = None, fn: int = 96):
        self.output_path = output_path
        self.fn = int(fn)

    def build(self, text: str):
        design = generate_design(text)
        scad = design_to_scad(design, fn=self.fn)
        return TextCADDocument(prompt=text, design=design, scad=scad)

    def to_scad(self, text: str) -> str:
        return self.build(text).scad

    def export(self, text: str, output_path: Optional[str] = None) -> str:
        doc = self.build(text)
        path = Path(output_path or self.output_path or "output.scad")
        path.write_text(doc.scad, encoding="utf-8")
        return str(path)

    def __call__(self, text: str):
        return self.build(text)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert text prompts into OpenSCAD")
    parser.add_argument("prompt", nargs="+", help="Natural language CAD prompt")
    parser.add_argument("-o", "--output", default="text_to_cad.scad")
    parser.add_argument("--fn", type=int, default=96)
    args = parser.parse_args()

    prompt = " ".join(args.prompt)
    generator = TextToCAD(output_path=args.output, fn=args.fn)
    out = generator.export(prompt)
    print(out)
