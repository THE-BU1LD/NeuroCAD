"""Through-wall cutter contracts and independent native blind-pocket regression."""
from __future__ import annotations

import shutil
from dataclasses import replace

import pytest

from core.artifacts import compile_scad_verified
from core.enclosure import (
    CutoutSpec, EnclosureSpec, LidSpec, VentPatternSpec,
    _cutout_node, _lid_cutout_node, _lid_vent_nodes, _vent_nodes, build_enclosure,
)
from core.enclosure_verification import verify_enclosure_mesh
from core.ir import Transform
from core.ir_export import program_to_scad


FACES = ('front', 'rear', 'left', 'right', 'bottom')


def spec_for(face, kind='rectangular', *, wall=2.4, floor=3.0, lip=4.0, vent=False):
    cutout = CutoutSpec('opening', kind, face, (0.0, 0.0),
                        size_mm=(10.0, 6.0) if kind == 'rectangular' else None,
                        diameter_mm=6.0 if kind == 'circular' else None)
    return EnclosureSpec(
        outer_size_mm=(80.0, 60.0, 30.0), wall_mm=wall, floor_mm=floor,
        profile='fdm_standard', lid=LidSpec('friction', 2.5, 0.3, lip_height_mm=lip),
        cutouts=() if vent else (cutout,),
        vents=(VentPatternSpec('air', face, (0.0, 0.0), 1, 1, 6.0, 8.0),) if vent else (),
    )


def normal_axis(face):
    return 1 if face in ('front', 'rear') else 0 if face in ('left', 'right') else 2


def cutter_extent(node, face):
    assert node.primitive is not None
    axis = normal_axis(face)
    parameters = node.primitive.parameters
    size = parameters['height'] if node.primitive.kind == 'cylinder' else parameters['size'][axis]
    center = node.transform.translate[axis]
    return center - size / 2, center + size / 2


@pytest.mark.parametrize('face', FACES)
@pytest.mark.parametrize('kind', ['rectangular', 'circular'])
@pytest.mark.parametrize('thickness', [1.6, 2.0, 2.4, 5.0])
def test_body_cutters_extend_one_mm_past_both_wall_faces(face, kind, thickness):
    spec = spec_for(face, kind, wall=thickness, floor=thickness)
    node = _cutout_node(spec.cutouts[0], spec)
    axis = normal_axis(face)
    half = spec.outer_size_mm[axis] / 2
    low, high = (-half, -half + thickness) if face in ('front', 'left', 'bottom') else (half - thickness, half)
    assert cutter_extent(node, face) == pytest.approx((low - 1, high + 1))


@pytest.mark.parametrize('kind', ['rectangular', 'circular'])
@pytest.mark.parametrize('lip', [0.0, 2.0, 4.0, 6.0])
def test_lid_cutters_clear_full_plate_and_plug(kind, lip):
    spec = spec_for('top', kind, lip=lip)
    node = _lid_cutout_node(spec.cutouts[0], spec)
    assert cutter_extent(node, 'top') == pytest.approx((-spec.lid.thickness_mm / 2 - lip - 1, spec.lid.thickness_mm / 2 + 1))


@pytest.mark.parametrize('face', [*FACES, 'top'])
def test_vents_share_the_corrected_cutter_placement(face):
    spec = spec_for(face, vent=True)
    nodes = _lid_vent_nodes(spec.vents[0], spec) if face == 'top' else _vent_nodes(spec.vents[0], spec)
    assert len(nodes) == 1
    cutout = CutoutSpec('air_1_1', 'circular', face, (0.0, 0.0), diameter_mm=6.0, purpose='vent')
    expected = _lid_cutout_node(cutout, spec) if face == 'top' else _cutout_node(cutout, spec)
    assert nodes[0] == expected


@pytest.mark.skipif(shutil.which('openscad') is None, reason='OpenSCAD is not installed')
@pytest.mark.parametrize('face,kind,vent', [
    ('front', 'rectangular', False), ('rear', 'circular', False),
    ('left', 'circular', False), ('right', 'rectangular', False),
    ('bottom', 'rectangular', False), ('top', 'rectangular', False),
    ('front', 'circular', True), ('top', 'circular', True),
])
def test_real_mesh_rejects_legacy_blind_caps_and_accepts_through_cuts(tmp_path, face, kind, vent):
    spec = spec_for(face, kind, vent=vent)
    part = 'lid' if face == 'top' else 'body'
    program = build_enclosure(spec).parts[part]
    target = 'air_1_1' if vent else 'opening'
    axis = normal_axis(face)
    sign = -1 if face in ('front', 'left', 'bottom') else 1
    legacy_center = 0.0 if face == 'top' else sign * spec.outer_size_mm[axis] / 2
    changed = []
    for node in program.nodes:
        if node.id == target:
            translation = list(node.transform.translate)
            translation[axis] = legacy_center
            node = replace(node, transform=Transform(tuple(translation), node.transform.rotate))
        changed.append(node)
    legacy = replace(program, nodes=tuple(changed))
    results = {}
    for label, candidate in [('fixed', program), ('legacy_blind', legacy)]:
        scad = tmp_path / f'{label}.scad'
        stl = tmp_path / f'{label}.stl'
        scad.write_text(program_to_scad(candidate, fn=32), encoding='utf-8')
        compile_scad_verified(scad, stl, timeout=120)
        results[label] = verify_enclosure_mesh(stl, spec, part=part)
    assert results['fixed'].valid, results['fixed'].to_dict()
    assert not results['legacy_blind'].valid
    failures = [probe for probe in results['legacy_blind'].probes if not probe.passed]
    assert any('inner depth' in probe.check for probe in failures)
    # The former center-only acceptance rule really would have accepted this cap.
    assert all(probe.passed for probe in results['legacy_blind'].probes if 'depth' not in probe.check)
