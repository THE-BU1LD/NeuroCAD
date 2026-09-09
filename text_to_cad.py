from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.artifacts import write_text_atomic
from core.design_graph import DesignGraph
from core.ir import CADProgram, IRValidationReport, validate_program
from core.ir_adapter import design_graph_to_ir
from core.ir_export import program_to_scad
from core.prompt_engine import generate_design
from core.validation import ValidationReport, validate_design


@dataclass
class TextCADDocument:
    prompt: str
    design: DesignGraph
    program: CADProgram | None
    scad: str
    validation: ValidationReport
    ir_validation: IRValidationReport | None

    def require_program(self) -> CADProgram:
        if self.program is None or not self.validation.valid:
            raise ValueError("invalid design: " + "; ".join(self.validation.errors))
        return self.program


class TextToCAD:
    def __init__(self, output_path: str | None = None, fn: int = 96):
        if not isinstance(fn, int) or isinstance(fn, bool) or not 3 <= fn <= 1000:
            raise ValueError("fn must be an integer between 3 and 1000")
        self.output_path = output_path
        self.fn = fn

    def build(self, text: str) -> TextCADDocument:
        design = generate_design(text)
        validation = validate_design(design)
        if not validation.valid:
            return TextCADDocument(
                prompt=text,
                design=design,
                program=None,
                scad="",
                validation=validation,
                ir_validation=None,
            )
        program = design_graph_to_ir(design)
        ir_validation = validate_program(program)
        if not ir_validation.valid:
            for issue in ir_validation.errors:
                validation.error(f"canonical IR {issue.path}: {issue.code}: {issue.message}")
        scad = program_to_scad(program, fn=self.fn)
        return TextCADDocument(
            prompt=text,
            design=design,
            program=program,
            scad=scad,
            validation=validation,
            ir_validation=ir_validation,
        )

    def to_scad(self, text: str) -> str:
        doc = self.build(text)
        doc.require_program()
        return doc.scad

    def export(self, text: str, output_path: str | None = None) -> str:
        doc = self.build(text)
        doc.require_program()
        path = Path(output_path or self.output_path or "output.scad")
        write_text_atomic(path, doc.scad)
        return str(path)

    def __call__(self, text: str) -> TextCADDocument:
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
