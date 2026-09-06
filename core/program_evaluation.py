from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .ir import CADProgram, Node, validate_program
from .ir_export import program_to_scad
from .ir_parser import parse_ir_json, serialize_ir_json


@dataclass(frozen=True)
class ProgramEvaluation:
    syntactic_validity: bool
    structural_validity: bool
    geometric_validity: bool | None
    kernel_validity: bool | None
    constraint_satisfaction_rate: float
    exact_round_trip: bool
    deterministic_export: bool
    editable_nodes: int
    node_count: int
    primitive_count: int
    hierarchy_depth: int
    serialized_bytes: int
    scad_bytes: int
    evaluation_latency_ms: float
    topology_correct: bool | None = None
    mesh_measurements: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "syntactic_validity": self.syntactic_validity,
            "structural_validity": self.structural_validity,
            "geometric_validity": self.geometric_validity,
            "kernel_validity": self.kernel_validity,
            "constraint_satisfaction_rate": self.constraint_satisfaction_rate,
            "exact_round_trip": self.exact_round_trip,
            "deterministic_export": self.deterministic_export,
            "editable_nodes": self.editable_nodes,
            "node_count": self.node_count,
            "primitive_count": self.primitive_count,
            "hierarchy_depth": self.hierarchy_depth,
            "serialized_bytes": self.serialized_bytes,
            "scad_bytes": self.scad_bytes,
            "evaluation_latency_ms": self.evaluation_latency_ms,
            "topology_correct": self.topology_correct,
            "mesh_measurements": self.mesh_measurements,
        }


def _depth(node: Node, node_map: dict[str, Node]) -> int:
    if not node.children:
        return 1
    return 1 + max(_depth(node_map[child], node_map) for child in node.children)


def evaluate_program(program: CADProgram, *, mesh_measurements: dict[str, Any] | None = None) -> ProgramEvaluation:
    started = perf_counter()
    report = validate_program(program)
    encoded = serialize_ir_json(program) if report.valid else ""
    exact_round_trip = False
    deterministic_export = False
    scad = ""
    if report.valid:
        recovered = parse_ir_json(encoded)
        exact_round_trip = recovered.to_dict() == program.to_dict()
        first = program_to_scad(program)
        second = program_to_scad(recovered)
        deterministic_export = first == second
        scad = first
    constraint_results = report.constraint_results
    constraint_rate = (
        sum(bool(result["satisfied"]) for result in constraint_results) / len(constraint_results)
        if constraint_results
        else 1.0
    )
    node_map = program.node_map()
    depth = max((_depth(node_map[root], node_map) for root in program.roots if root in node_map), default=0) if report.valid else 0
    primitive_count = sum(node.primitive is not None for node in program.nodes)
    editable_nodes = sum(node.primitive is not None and bool(node.primitive.parameters) for node in program.nodes)
    kernel_validity: bool | None = None
    topology_correct: bool | None = None
    if mesh_measurements is not None:
        kernel_validity = bool(
            mesh_measurements.get("kernel_validity", True)
            and mesh_measurements.get("watertight")
            and mesh_measurements.get("winding_consistent")
            and mesh_measurements.get("finite_vertices")
            and mesh_measurements.get("is_volume")
            and mesh_measurements.get("body_count") == 1
        )
        topology_correct = kernel_validity
    return ProgramEvaluation(
        syntactic_validity=bool(encoded),
        structural_validity=report.valid,
        # Kept as a compatibility field for existing result consumers, but it
        # now means kernel-backed validity and is unknown without a verified
        # mesh.  Static IR/AABB validation is reported separately above.
        geometric_validity=kernel_validity,
        kernel_validity=kernel_validity,
        constraint_satisfaction_rate=constraint_rate,
        exact_round_trip=exact_round_trip,
        deterministic_export=deterministic_export,
        editable_nodes=editable_nodes,
        node_count=len(program.nodes),
        primitive_count=primitive_count,
        hierarchy_depth=depth,
        serialized_bytes=len(encoded.encode("utf-8")),
        scad_bytes=len(scad.encode("utf-8")),
        evaluation_latency_ms=(perf_counter() - started) * 1000,
        topology_correct=topology_correct,
        mesh_measurements=mesh_measurements,
    )
