#!/usr/bin/env python3
"""Independently inspect retained linear MSH 4.1 meshes without importing Gmsh.

The supported ASCII subset is deliberately narrow. Incidence and Euler checks
are diagnostics, not a proof of embeddedness, physical validity or CAD identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_mesh(path: Path):
    data = path.read_bytes()
    if len(data) > 64_000_000:
        raise ValueError("reference analysis is limited to 64 MB ASCII files")
    lines = data.decode("ascii").splitlines()
    sections = {}
    i = 0
    while i < len(lines):
        tag = lines[i].strip()
        if not tag.startswith("$") or tag.startswith("$End"):
            raise ValueError("malformed section boundary")
        name = tag[1:]
        if name in sections:
            raise ValueError("duplicate section")
        try:
            end = lines.index("$End" + name, i+1)
        except ValueError as exc:
            raise ValueError("missing section terminator") from exc
        sections[name] = lines[i+1:end]
        i = end+1
    if sections.get("MeshFormat") != ["4.1 0 8"]:
        raise ValueError("only ASCII MSH 4.1 with 8-byte reals is supported")
    nodes = {}
    section = sections.get("Nodes", [])
    if not section:
        raise ValueError("missing nodes")
    header = [int(x) for x in section[0].split()]
    if len(header) != 4 or header[0] < 1 or header[1] < 4:
        raise ValueError("invalid node header")
    tokens = iter(" ".join(section[1:]).split())
    try:
        for _ in range(header[0]):
            dim, entity, parametric, count = [int(next(tokens)) for _ in range(4)]
            if dim not in range(4) or entity <= 0 or parametric != 0 or not 0 <= count <= header[1]:
                raise ValueError("unsupported node block")
            tags = [int(next(tokens)) for _ in range(count)]
            for tag in tags:
                xyz = tuple(float(next(tokens)) for _ in range(3))
                if tag <= 0 or tag in nodes or not all(math.isfinite(x) for x in xyz):
                    raise ValueError("duplicate/invalid node or nonfinite coordinate")
                nodes[tag] = xyz
    except StopIteration as exc:
        raise ValueError("truncated node section") from exc
    if next(tokens, None) is not None or len(nodes) != header[1] or min(nodes) != header[2] or max(nodes) != header[3]:
        raise ValueError("node counts or tag bounds disagree")
    section = sections.get("Elements", [])
    if not section:
        raise ValueError("missing elements")
    header = [int(x) for x in section[0].split()]
    if len(header) != 4 or header[0] < 1 or header[1] < 1:
        raise ValueError("invalid element header")
    tokens = iter(" ".join(section[1:]).split())
    identifiers, tetrahedra, surface = set(), [], []
    kinds = {15:(0,1), 1:(1,2), 2:(2,3), 4:(3,4)}
    try:
        for _ in range(header[0]):
            dim, entity, kind, count = [int(next(tokens)) for _ in range(4)]
            if kind not in kinds or kinds[kind][0] != dim or entity <= 0 or not 0 <= count <= header[1]:
                raise ValueError("unsupported element block; linear simplices only")
            for _ in range(count):
                identifier = int(next(tokens))
                element = tuple(int(next(tokens)) for _ in range(kinds[kind][1]))
                if identifier <= 0 or identifier in identifiers or len(set(element)) != len(element) or any(tag not in nodes for tag in element):
                    raise ValueError("duplicate/invalid element or missing node")
                identifiers.add(identifier)
                if kind == 4:
                    tetrahedra.append(element)
                elif kind == 2:
                    surface.append(element)
    except StopIteration as exc:
        raise ValueError("truncated element section") from exc
    if next(tokens, None) is not None or len(identifiers) != header[1] or min(identifiers) != header[2] or max(identifiers) != header[3]:
        raise ValueError("element counts or tag bounds disagree")
    return nodes, tetrahedra, surface


def parity(face):
    return -1 if sum(face[i] > face[j] for i in range(len(face)) for j in range(i+1,len(face))) % 2 else 1


def signed_volume(points):
    a,b,c,d = points
    u,v,w = [[p[k]-a[k] for k in range(3)] for p in (b,c,d)]
    return (u[0]*(v[1]*w[2]-v[2]*w[1])-u[1]*(v[0]*w[2]-v[2]*w[0])+u[2]*(v[0]*w[1]-v[1]*w[0]))/6


def components(adjacency):
    unseen = set(adjacency)
    count = 0
    while unseen:
        count += 1
        pending = [unseen.pop()]
        while pending:
            for neighbor in adjacency[pending.pop()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    pending.append(neighbor)
    return count


def inspect_complex(nodes, tetrahedra, surface=None):
    if not tetrahedra:
        raise ValueError("no tetrahedra")
    if len({tuple(sorted(t)) for t in tetrahedra}) != len(tetrahedra):
        raise ValueError("duplicate tetrahedra")
    faces, edges = defaultdict(list), set()
    used = set()
    volumes = []
    dual = {i:set() for i in range(len(tetrahedra))}
    for i, tet in enumerate(tetrahedra):
        if len(tet) != 4 or len(set(tet)) != 4 or any(tag not in nodes for tag in tet):
            raise ValueError("invalid tetrahedron connectivity")
        points = [nodes[tag] for tag in tet]
        if any(len(p) != 3 or not all(math.isfinite(x) for x in p) for p in points):
            raise ValueError("invalid coordinates")
        volume = signed_volume(points)
        if not math.isfinite(volume) or volume <= 0:
            raise ValueError("nonpositive tetrahedron orientation")
        volumes.append(volume)
        used.update(tet)
        edges.update(tuple(sorted(edge)) for edge in combinations(tet,2))
        a,b,c,d = tet
        for face in ((b,c,d),(a,d,c),(a,b,d),(a,c,b)):
            faces[tuple(sorted(face))].append((i,parity(face),face))
    boundary = []
    for key, owners in faces.items():
        if len(owners) == 1:
            boundary.append(owners[0][2])
        elif len(owners) == 2 and owners[0][1] + owners[1][1] == 0:
            i,j = owners[0][0],owners[1][0]
            dual[i].add(j)
            dual[j].add(i)
        else:
            raise ValueError("nonmanifold or inconsistently oriented interior face")
    edge_faces = defaultdict(list)
    edge_sign = Counter()
    boundary_nodes = set()
    for i, (a,b,c) in enumerate(boundary):
        boundary_nodes.update((a,b,c))
        for edge in ((a,b),(b,c),(c,a)):
            key = tuple(sorted(edge))
            edge_faces[key].append(i)
            edge_sign[key] += parity(edge)
    if any(len(owners) != 2 or edge_sign[edge] != 0 for edge,owners in edge_faces.items()):
        raise ValueError("boundary edge does not have two opposite incidences")
    boundary_dual = {i:set() for i in range(len(boundary))}
    for owners in edge_faces.values():
        i,j = owners
        boundary_dual[i].add(j)
        boundary_dual[j].add(i)
    boundary_set = {tuple(sorted(face)) for face in boundary}
    if surface is not None:
        surface_set = {tuple(sorted(face)) for face in surface}
        if len(surface_set) != len(surface) or surface_set != boundary_set:
            raise ValueError("serialized surface triangles do not equal tetrahedral boundary")
    return {"vertices":len(used), "edges":len(edges), "faces":len(faces), "tetrahedra":len(tetrahedra), "euler_volume":len(used)-len(edges)+len(faces)-len(tetrahedra), "boundary_vertices":len(boundary_nodes), "boundary_edges":len(edge_faces), "boundary_faces":len(boundary), "euler_boundary":len(boundary_nodes)-len(edge_faces)+len(boundary), "volume_components":components(dual), "boundary_components":components(boundary_dual), "volume_mm3":math.fsum(volumes), "minimum_oriented_tet_volume_mm3":min(volumes), "surface_equals_tetrahedral_boundary":surface is not None, "interior_face_orientation":"opposite", "boundary_edge_incidence":"two_opposite", "unused_serialized_nodes":len(nodes)-len(used)}


def run(bundle: Path, output: Path):
    original = json.loads((bundle/'summary.json').read_text())
    manifest = json.loads((bundle/'SHA256SUMS.json').read_text())
    for name, expected in manifest.items():
        if digest(bundle/name) != expected:
            raise ValueError(f"retained evidence changed: {name}")
    records = []
    for case in original['cases']:
        path = bundle/case['bundle']/'design.msh'
        nodes,tets,surface = parse_mesh(path)
        measured = inspect_complex(nodes,tets,surface)
        expected_euler = 1 if case['part'] == 'box' else 0
        if measured['euler_volume'] != expected_euler or measured['euler_boundary'] != 2*expected_euler or measured['volume_components'] != 1 or measured['boundary_components'] != 1:
            raise ValueError("reference topology diagnostic differs from analytic expectation")
        if measured['tetrahedra'] != case['tetrahedra'] or not math.isclose(measured['volume_mm3'],case['volume_mm3'],rel_tol=1e-12,abs_tol=1e-9):
            raise ValueError("independent ASCII parse/volume does not reproduce retained count or volume")
        records.append({"part":case['part'],"max_size_mm":case['max_size_mm'],"mesh_sha256":digest(path),"relative_volume_error":case['relative_volume_error'],"minimum_sicn_retained":case['minimum_sicn'],**measured})
    output.mkdir(parents=True,exist_ok=False)
    result = {"protocol":"NEUROCAD_RETAINED_MESH_TOPOLOGY_V1", "status":"PASS", "source_bundle_protocol":original['protocol'], "verified_original_artifact_hashes":len(manifest), "source_summary_sha256":digest(bundle/'summary.json'), "source_manifest_sha256":digest(bundle/'SHA256SUMS.json'), "analyzer_sha256":digest(Path(__file__)), "cases":records, "limits":["This is analysis of the six existing meshes; no mesher rerun, parameter selection or new empirical corpus.","Face/edge incidences, connectivity and Euler values do not alone prove geometric embeddedness, vertex-link manifoldness or exact CAD equivalence.","Element intersections, thin-feature fidelity, solver convergence, safety and learned-generation quality are not assessed.","Reported SICN values are retained upstream values; this Gmsh-independent analysis recomputes connectivity and oriented volumes only."]}
    (output/'summary.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run(args.bundle.resolve(),args.output)
    print(json.dumps({"status":result['status'],"cases":len(result['cases']),"verified_original_hashes":result['verified_original_artifact_hashes']}))
