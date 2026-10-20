"""Small flat coupons retaining a supported enclosure cutout's generated dimensions."""

from __future__ import annotations

import hashlib
import math

from .enclosure import build_enclosure
from .ir import CADProgram, Node, Primitive, Transform
from .project import EnclosureProject, serialize_project


def cutout_fit_sample(
    project: EnclosureProject,
    cutout_id: str,
    *,
    margin_mm: float = 5.0,
    aperture_adjustment_mm: float = 0.0,
    marker_code: int | None = None,
) -> CADProgram:
    """Extract one rectangular/circular aperture from the validated body compiler.

    The coupon is flat in XY. Geometry agreement is not evidence that its print
    orientation or physical fit transfers to the assembled enclosure.
    """
    if isinstance(margin_mm, bool) or not math.isfinite(margin_mm) or not 2 <= margin_mm <= 50:
        raise ValueError("sample margin must be between 2 and 50 mm")
    if (
        isinstance(aperture_adjustment_mm, bool)
        or not isinstance(aperture_adjustment_mm, (int, float))
        or not math.isfinite(float(aperture_adjustment_mm))
        or not -5 <= float(aperture_adjustment_mm) <= 5
    ):
        raise ValueError("aperture adjustment must be a finite number between -5 and 5 mm")
    adjustment = float(aperture_adjustment_mm)
    if marker_code is not None and (
        isinstance(marker_code, bool) or not isinstance(marker_code, int) or not 1 <= marker_code <= 31
    ):
        raise ValueError("marker code must be an integer between 1 and 31")
    if marker_code is not None and margin_mm < 5:
        raise ValueError("physically marked fit samples require at least 5 mm of margin")
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
        nominal_radius = float(source.primitive.parameters["radius"])
        nominal_width = nominal_height = 2 * nominal_radius
        width = height = nominal_width + adjustment
        if width < 0.1:
            raise ValueError("aperture adjustment produces a diameter below 0.1 mm")
        aperture = Primitive("cylinder", {"radius": width / 2, "height": thickness + 2})
    else:
        size = source.primitive.parameters["size"]
        axes = (0, 2) if cutout.face in {"front", "rear"} else (1, 2) if cutout.face in {"left", "right"} else (0, 1)
        nominal_width, nominal_height = float(size[axes[0]]), float(size[axes[1]])
        width, height = nominal_width + adjustment, nominal_height + adjustment
        if min(width, height) < 0.1:
            raise ValueError("aperture adjustment produces a dimension below 0.1 mm")
        aperture = Primitive("box", {"size": [width, height, thickness + 2]})
    nodes = [
        Node(
            "sample_blank",
            primitive=Primitive("box", {"size": [width + 2 * margin_mm, height + 2 * margin_mm, thickness]}),
        ),
        Node("sample_aperture", primitive=aperture, role="cutout"),
    ]
    cutouts = ["sample_aperture"]
    marker_description = None
    if marker_code is not None:
        # A fixed anchor plus five binary through-holes makes the printed variant
        # recoverable without relying on filenames or handwritten labels.  The
        # code lives entirely in the top margin and does not touch the aperture.
        marker_y = height / 2 + margin_mm / 2
        marker_radius = 0.25
        marker_pitch = 0.9
        marker_positions = ((-2.5 + index) * marker_pitch for index in range(6))
        for index, marker_x in enumerate(marker_positions):
            present = index == 0 or bool(marker_code & (1 << (index - 1)))
            if not present:
                continue
            marker_id = "sample_marker_anchor" if index == 0 else f"sample_marker_bit_{index - 1}"
            nodes.append(
                Node(
                    marker_id,
                    primitive=Primitive("cylinder", {"radius": marker_radius, "height": thickness + 2}),
                    transform=Transform(translate=(marker_x, marker_y, 0)),
                    role="cutout",
                )
            )
            cutouts.append(marker_id)
        marker_description = {
            "code": marker_code,
            "encoding": "fixed left anchor followed by five little-endian binary through-hole positions",
            "hole_diameter_mm": 2 * marker_radius,
            "pitch_mm": marker_pitch,
            "location": "top coupon margin",
        }
    nodes.append(Node("sample", composition="difference", children=("sample_blank", *cutouts)))
    return CADProgram(
        title=f"Fit sample: {cutout_id}",
        nodes=tuple(nodes),
        roots=("sample",),
        metadata={
            "source_project_sha256": hashlib.sha256(serialize_project(project).encode()).hexdigest(),
            "source_project_id": project.project_id,
            "source_revision": project.revision,
            "source_cutout_id": cutout_id,
            "source_face": cutout.face,
            "aperture_size_mm": [width, height],
            "nominal_aperture_size_mm": [nominal_width, nominal_height],
            "aperture_adjustment_mm": adjustment,
            "aperture_adjustment_definition": (
                "total diameter adjustment for circular apertures; total width and height adjustment "
                "for rectangular apertures"
            ),
            "wall_thickness_mm": thickness,
            "margin_mm": margin_mm,
            "physical_marker": marker_description,
            "orientation": "flat XY; orient deliberately to match the target manufacturing process",
            "evidence": "generated geometry only; no physical fit or print-time claim",
        },
    )
