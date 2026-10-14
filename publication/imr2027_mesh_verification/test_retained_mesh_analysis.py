import tempfile
import unittest
from pathlib import Path

from analyze_retained_meshes import inspect_complex, parse_mesh


class ComplexChecks(unittest.TestCase):
    def setUp(self):
        self.nodes = {
            1: (0.0, 0.0, 0.0),
            2: (1.0, 0.0, 0.0),
            3: (0.0, 1.0, 0.0),
            4: (0.0, 0.0, 1.0),
        }
        self.tet = (1, 2, 3, 4)

    def test_tetrahedron_has_ball_and_sphere_euler_values(self):
        result = inspect_complex(self.nodes, [self.tet])
        self.assertEqual(
            (
                result["vertices"],
                result["edges"],
                result["faces"],
                result["tetrahedra"],
            ),
            (4, 6, 4, 1),
        )
        self.assertEqual((result["euler_volume"], result["euler_boundary"]), (1, 2))
        self.assertAlmostEqual(result["volume_mm3"], 1 / 6)

    def test_inverted_tetrahedron_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "orientation"):
            inspect_complex(self.nodes, [(2, 1, 3, 4)])

    def test_duplicate_tetrahedron_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            inspect_complex(self.nodes, [self.tet, self.tet])

    def test_surface_missing_one_triangle_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "surface"):
            inspect_complex(self.nodes, [self.tet], [(1, 2, 3), (1, 2, 4), (1, 3, 4)])

    def test_nonfinite_coordinate_is_rejected(self):
        self.nodes[1] = (float("nan"), 0.0, 0.0)
        with self.assertRaisesRegex(ValueError, "coordinates"):
            inspect_complex(self.nodes, [self.tet])

    def test_missing_node_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "connectivity"):
            inspect_complex(self.nodes, [(1, 2, 3, 99)])

    def test_disconnected_valid_tetrahedra_are_reported_not_hidden(self):
        nodes = {
            **self.nodes,
            **{k + 4: (x + 3, y, z) for k, (x, y, z) in self.nodes.items()},
        }
        result = inspect_complex(nodes, [self.tet, (5, 6, 7, 8)])
        self.assertEqual(
            (result["volume_components"], result["boundary_components"]), (2, 2)
        )

    def test_same_side_overlap_at_shared_face_is_rejected(self):
        self.nodes[5] = (0.0, 0.0, 2.0)
        with self.assertRaisesRegex(ValueError, "interior face"):
            inspect_complex(self.nodes, [self.tet, (1, 2, 3, 5)])

    def test_duplicate_section_and_unsupported_format_rejected(self):
        for body in (
            "$MeshFormat\n4.1 1 8\n$EndMeshFormat\n",
            "$MeshFormat\n4.1 0 8\n$EndMeshFormat\n$MeshFormat\n4.1 0 8\n$EndMeshFormat\n",
        ):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "bad.msh"
                path.write_text(body)
                with self.assertRaises(ValueError):
                    parse_mesh(path)


if __name__ == "__main__":
    unittest.main()
