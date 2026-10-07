#!/usr/bin/env python3
"""Render actual retained boundary triangles and a one-page research-note handout."""

import argparse
import json
from pathlib import Path
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)

from analyze_retained_meshes import parse_mesh

FONT_DIR = Path(
    os.environ.get("PRESENTATION_FONT_DIR", "/usr/share/fonts/truetype/dejavu")
)
pdfmetrics.registerFont(TTFont("HandoutBody", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("HandoutBold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("HandoutBody", normal="HandoutBody", bold="HandoutBold")
ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--bundle", type=Path, required=True)
args = parser.parse_args()
summary = json.loads((ROOT / "evidence/retained-topology-v1/summary.json").read_text())
(ROOT / "figures").mkdir(exist_ok=True)
fig = plt.figure(figsize=(7, 3.2), layout="constrained")
for i, (part, title) in enumerate(
    [
        ("box", "Box: upper boundary"),
        ("holed_plate", "Plate: upper boundary"),
    ]
):
    nodes, tets, surface = parse_mesh(args.bundle / part / "size-4mm/design.msh")
    top_z = max(point[2] for point in nodes.values())
    top_surface = [
        tri for tri in surface if all(abs(nodes[j][2] - top_z) < 1e-9 for j in tri)
    ]
    if not top_surface:
        raise ValueError("No planar upper boundary triangles found")
    ax = fig.add_subplot(1, 2, i + 1)
    collection = PolyCollection(
        [[nodes[j][:2] for j in tri] for tri in top_surface],
        facecolors="#7ab1bd",
        edgecolors="#255362",
        linewidths=0.25,
        alpha=1,
    )
    ax.add_collection(collection)
    ax.set(
        xlim=(-0.5, 20.5),
        ylim=(-0.5, 12.5),
        title=title,
        xlabel="x (mm)",
        ylabel="y (mm)",
    )
    ax.set_aspect("equal")
    ax.tick_params(labelsize=7)
fig.savefig(ROOT / "figures/retained_boundaries.png", dpi=240)
plt.close(fig)
navy = colors.HexColor("#173646")
teal = colors.HexColor("#156d88")
styles = {
    "tag": ParagraphStyle(
        "tag", fontName="HandoutBold", fontSize=9, textColor=teal, spaceAfter=12
    ),
    "title": ParagraphStyle(
        "title",
        fontName="HandoutBold",
        fontSize=23,
        leading=27,
        textColor=navy,
        spaceAfter=12,
    ),
    "body": ParagraphStyle(
        "body", fontName="HandoutBody", fontSize=10.2, leading=13.5, spaceAfter=8
    ),
    "small": ParagraphStyle(
        "small", fontName="HandoutBody", fontSize=8.6, leading=11, spaceAfter=7
    ),
    "section": ParagraphStyle(
        "section",
        fontName="HandoutBold",
        fontSize=12,
        leading=15,
        textColor=navy,
        spaceBefore=7,
        spaceAfter=7,
    ),
}
story = [
    Paragraph("SIAM IMR27 | AUTHOR-REVIEW PRESENTATION HANDOUT", styles["tag"]),
    Paragraph(
        "Read the published mesh.<br/>Check what the file contains.", styles["title"]
    ),
    Paragraph(
        "Six retained native meshes. Two analytic solids. Independent ASCII parsing, oriented volumes and boundary incidence without importing Gmsh.",
        styles["body"],
    ),
    Image(str(ROOT / "figures/retained_boundaries.png"), width=500, height=229),
]
data = [
    ["Reference", "Elements", "Volume error", "Solid / boundary Euler"],
    ["Box", "643-5,033", "0% at shown precision", "1 / 2"],
    ["Through-hole plate", "736-4,838", "0.154483-0.526629%", "0 / 0"],
]
table = Table(data, colWidths=[135, 92, 130, 165])
table.setStyle(
    TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "HandoutBody"),
            ("BACKGROUND", (0, 0), (-1, 0), navy),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "HandoutBold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.4),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.HexColor("#eef5f7"), colors.white],
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]
    )
)
story += [
    table,
    Spacer(1, 8),
    Paragraph("What was checked", styles["section"]),
    Paragraph(
        "All 16 original artifact hashes remain unchanged. Each mesh has one volume component and one boundary component; shared interior faces and boundary edges have opposite orientations. Stored surface triangles equal the boundary derived from tetrahedra.",
        styles["body"],
    ),
    Paragraph("What the result does not establish", styles["section"]),
    Paragraph(
        "Euler counts and incidence checks do not prove embeddedness, vertex-link manifoldness or exact CAD equivalence. No industrial corpus, solver convergence, structural-safety or learned-model result is claimed.",
        styles["body"],
    ),
    Paragraph(
        "10-minute talk: failure mode (1.5 min), reference parts and hashes (2 min), determinant/incidence checks (3 min), six-case results (2 min), limits and reuse (1.5 min). IMR provides a further 5 minutes for questions. Author approval and registration remain separate from this prepared material.",
        styles["small"],
    ),
]
SimpleDocTemplate(
    str(ROOT / "presentation_handout.pdf"),
    pagesize=(612, 792),
    rightMargin=45,
    leftMargin=45,
    topMargin=36,
    bottomMargin=32,
    title="Retained mesh verification: presentation handout",
    author="",
).build(story)
