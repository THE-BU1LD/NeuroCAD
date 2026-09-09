"""Small flat coupons retaining a supported enclosure cutout's generated dimensions."""

from __future__ import annotations

import hashlib
import math

from .enclosure import build_enclosure
from .ir import CADProgram, Node, Primitive
from .project import EnclosureProject, serialize_project


def cutout_fit_sample(project: EnclosureProject, cutout_id: str, *, margin_mm: float = 5.0) -> CADProgram:
    """Extract one rectangular/circular aperture from the validated body compiler.

    The coupon is flat in XY. Geometry agreement is not evidence that its print
    orientation or physical fit transfers to the assembled enclosure.
    """
    if isinstance(margin_mm, bool) or not math.isfinite(margin_mm) or not 2 <= margin_mm <= 50:
        raise ValueError("sample margin must be between 2 and 50 mm")
    spec = project.spec
    build = build_enclosure(spec)
    cutout = next((item for item in spec.cutouts if item.id == cutout_id), None)
    if cutout is None:
        raise ValueError("cutout ID does not exist in this project")
    if cutout.face == "top" or cutout.corner_radius_mm:
        raise ValueError("fit samples currently support unrounded body cutouts, not lid cutouts")
    source = next(node for node in build.parts["body"].nodes if node.id == cutout_id)
    if source.primitive is None:
        raise ValueError("compiled cutout has no primitive geometry")
    thickness = (spec.floor_mm if spec.floor_mm is not None else spec.wall_mm) if cutout.face == "bottom" else spec.wall_mm
    if source.primitive.kind == "cylinder":
        radius = float(source.primitive.parameters["radius"])
        width = height = 2 * radius
        aperture = Primitive("cylinder", {"radius": radius, "height": thickness + 2})
    else:
        size = source.primitive.parameters["size"]
        axes = (0, 2) if cutout.face in {"front", "rear"} else (1, 2) if cutout.face in {"left", "right"} else (0, 1)
        width, height = float(size[axes[0]]), float(size[axes[1]])
        aperture = Primitive("box", {"size": [width, height, thickness + 2]})
    return CADProgram(
        title=f"Fit sample: {cutout_id}",
        nodes=(
            Node("sample_blank", primitive=Primitive("box", {"size": [width + 2 * margin_mm, height + 2 * margin_mm, thickness]})),
            Node("sample_aperture", primitive=aperture, role="cutout"),
            Node("sample", composition="difference", children=("sample_blank", "sample_aperture")),
        ),
        roots=("sample",),
        metadata={
            "source_project_sha256": hashlib.sha256(serialize_project(project).encode()).hexdigest(),
            "source_project_id": project.project_id,
            "source_revision": project.revision,
            "source_cutout_id": cutout_id,
            "source_face": cutout.face,
            "aperture_size_mm": [width, height],
            "wall_thickness_mm": thickness,
            "margin_mm": margin_mm,
            "orientation": "flat XY; orient deliberately to match the target manufacturing process",
            "evidence": "generated geometry only; no physical fit or print-time claim",
        },
    )
