"""Tests for the naming and number rules of the previs file tree."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from mise_stage.backends.previs_files import naming  # noqa: E402
from mise_stage.backends.previs_files.errors import (  # noqa: E402
    InvalidNameError,
    NumberOutOfRangeError,
    PrevisFilesError,
)


class ParseSceneNameTests(unittest.TestCase):
    def test_parses_all_parts(self) -> None:
        self.assertEqual(
            naming.parse_scene_name("abc_0100_a007_v012"),
            naming.SceneName("abc", 100, 7, 12),
        )

    def test_rejects_two_digit_version(self) -> None:
        with self.assertRaises(InvalidNameError):
            naming.parse_scene_name("abc_0100_a007_v12")

    def test_rejects_version_zero(self) -> None:
        with self.assertRaises(NumberOutOfRangeError):
            naming.parse_scene_name("abc_0100_a007_v000")

    def test_rejects_malformed_names(self) -> None:
        for bad in (
            "abc-0100-a007-v012",
            "abc_0100_a007",
            "abc_100_a007_v012",
            "_0100_a007_v012",
            "ab_c_0100_a007_v012",
            "abc_0100_a007_v012.ma",
            "abc_０１００_a007_v012",
            "",
            None,
        ):
            with self.subTest(name=bad):
                with self.assertRaises(InvalidNameError):
                    naming.parse_scene_name(bad)  # type: ignore[arg-type]


class BuildSceneNameTests(unittest.TestCase):
    def test_round_trips_edge_numbers(self) -> None:
        for sequence in (0, 9999):
            for action in (0, 999):
                for version in (1, 999):
                    with self.subTest(s=sequence, a=action, v=version):
                        name = naming.scene_name("abc", sequence, action, version)
                        self.assertEqual(
                            naming.parse_scene_name(name),
                            naming.SceneName("abc", sequence, action, version),
                        )

    def test_pads_to_fixed_widths(self) -> None:
        self.assertEqual(naming.scene_name("abc", 0, 0, 1), "abc_0000_a000_v001")

    def test_rejects_numbers_out_of_range(self) -> None:
        for args in (
            ("abc", 10000, 0, 1),
            ("abc", -1, 0, 1),
            ("abc", 0, 1000, 1),
            ("abc", 0, 0, 1000),
            ("abc", 0, 0, 0),
        ):
            with self.subTest(args=args):
                with self.assertRaises(NumberOutOfRangeError):
                    naming.scene_name(*args)

    def test_rejects_non_integer_numbers(self) -> None:
        for bad in ("100", 1.5, True):
            with self.subTest(value=bad):
                with self.assertRaises(NumberOutOfRangeError):
                    naming.sequence_dir_name(bad)  # type: ignore[arg-type]

    def test_rejects_bad_show_code(self) -> None:
        for bad in ("", "a b", "a_b", "../x", None):
            with self.subTest(show=bad):
                with self.assertRaises(InvalidNameError):
                    naming.scene_name(bad, 0, 0, 1)  # type: ignore[arg-type]

    def test_errors_share_one_base_class(self) -> None:
        with self.assertRaises(PrevisFilesError):
            naming.scene_name("abc", 10000, 0, 1)


class CheckExtensionTests(unittest.TestCase):
    def test_accepts_extensions_with_or_without_a_dot(self) -> None:
        self.assertEqual(naming.check_extension("ma"), "ma")
        self.assertEqual(naming.check_extension(".mb"), "mb")

    def test_rejects_anything_else(self) -> None:
        for bad in ("", ".", "ma/../x", "a.b", "m a", "..ma", "ma\\x", None, 5):
            with self.subTest(ext=bad):
                with self.assertRaises(InvalidNameError):
                    naming.check_extension(bad)


class FolderNameTests(unittest.TestCase):
    def test_builds_folder_names(self) -> None:
        self.assertEqual(naming.sequence_dir_name(0), "0000")
        self.assertEqual(naming.sequence_dir_name(100), "0100")
        self.assertEqual(naming.action_dir_name(0), "a000")
        self.assertEqual(naming.action_dir_name(7), "a007")
        self.assertEqual(naming.version_dir_name(1), "v001")
        self.assertEqual(naming.version_dir_name(999), "v999")

    def test_parses_valid_folder_names(self) -> None:
        self.assertEqual(naming.parse_sequence_dir("0100"), 100)
        self.assertEqual(naming.parse_sequence_dir("0000"), 0)
        self.assertEqual(naming.parse_action_dir("a007"), 7)
        self.assertEqual(naming.parse_version_dir("v003"), 3)

    def test_parse_returns_none_for_non_matching_names(self) -> None:
        for name in ("100", "00100", "notes", "a007", "０１００", ""):
            with self.subTest(name=name):
                self.assertIsNone(naming.parse_sequence_dir(name))
        for name in ("007", "a07", "a0007", "v007", "A007", "a００７"):
            with self.subTest(name=name):
                self.assertIsNone(naming.parse_action_dir(name))
        for name in ("003", "v03", "v0003", "v000", "a003", "V003"):
            with self.subTest(name=name):
                self.assertIsNone(naming.parse_version_dir(name))


if __name__ == "__main__":
    unittest.main()
