import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from mise_stage.backends.previs_files import (  # noqa: E402
    AlreadyExistsError,
    InvalidNameError,
    NotFoundError,
    NumberOutOfRangeError,
    PrevisFileStore,
)

SHOW = "abc"


def make_dirs(root, *parts):
    path = Path(root).joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def touch(path):
    path.write_text("")
    return path


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = PrevisFileStore(self.root, SHOW)

    def version_dir(self, sequence=100, action=7, version=1):
        return make_dirs(
            self.root,
            "sequences",
            f"{sequence:04d}",
            f"a{action:03d}",
            f"v{version:03d}",
        )


class ListingTests(StoreTestCase):
    def test_versions_without_scene_file_are_listed_and_flagged(self):
        v1 = self.version_dir(version=1)
        touch(v1 / "abc_0100_a007_v001.ma")
        self.version_dir(version=2)
        versions = self.store.list_versions(100, 7)
        self.assertEqual([v.number for v in versions], [1, 2])
        self.assertTrue(versions[0].has_scene)
        self.assertEqual(versions[1].scene_files, ())
        self.assertFalse(versions[1].has_scene)

    def test_unrelated_folders_and_files_are_ignored(self):
        make_dirs(self.root, "sequences", "0100", "a007")
        make_dirs(self.root, "sequences", "notes")
        touch(self.root / "sequences" / "readme.txt")
        touch(self.root / "sequences" / "0100" / "readme.txt")
        make_dirs(self.root, "sequences", "0100", "a07")
        make_dirs(self.root, "sequences", "0100", "007")
        make_dirs(self.root, "sequences", "0100", "a007", "v0003")
        make_dirs(self.root, "sequences", "0100", "a007", "v000")
        touch(self.root / "sequences" / "0100" / "a008")  # a file, not a folder
        self.assertEqual([s.number for s in self.store.list_sequences()], [100])
        self.assertEqual([a.number for a in self.store.list_actions(100)], [7])
        self.assertEqual(self.store.list_versions(100, 7), [])

    def test_scene_files_match_stem_with_any_extension_for_this_show(self):
        folder = self.version_dir(version=3)
        ma = touch(folder / "abc_0100_a007_v003.ma")
        mb = touch(folder / "abc_0100_a007_v003.mb")
        touch(folder / "abc_0100_a007_v003.ma.bak")
        touch(folder / "xyz_0100_a007_v003.ma")
        touch(folder / "meta.json")
        make_dirs(folder, "abc_0100_a007_v003.ma.dir")
        version = self.store.list_versions(100, 7)[0]
        self.assertEqual(version.scene_files, tuple(sorted((ma, mb))))

    def test_listings_are_in_numeric_order(self):
        for number in (200, 0, 100):
            make_dirs(self.root, "sequences", f"{number:04d}")
        for number in (10, 2, 1):
            make_dirs(self.root, "sequences", "0000", f"a{number:03d}")
        self.assertEqual([s.number for s in self.store.list_sequences()], [0, 100, 200])
        self.assertEqual([a.number for a in self.store.list_actions(0)], [1, 2, 10])

    def test_same_action_number_in_different_sequences_is_unrelated(self):
        self.version_dir(sequence=100, action=7, version=1)
        self.version_dir(sequence=200, action=7, version=1)
        self.version_dir(sequence=200, action=7, version=2)
        self.assertEqual(len(self.store.list_versions(100, 7)), 1)
        self.assertEqual(len(self.store.list_versions(200, 7)), 2)

    def test_missing_sequences_folder_lists_as_empty(self):
        self.assertEqual(self.store.list_sequences(), [])

    def test_missing_parents_are_not_found(self):
        with self.assertRaises(NotFoundError):
            PrevisFileStore(self.root / "nope", SHOW).list_sequences()
        with self.assertRaises(NotFoundError):
            self.store.list_actions(300)
        make_dirs(self.root, "sequences", "0300")
        with self.assertRaises(NotFoundError):
            self.store.list_versions(300, 1)

    def test_latest_version_is_highest_even_without_scene_file(self):
        touch(self.version_dir(version=1) / "abc_0100_a007_v001.ma")
        self.version_dir(version=2)
        self.assertEqual(self.store.latest_version(100, 7).number, 2)

    def test_latest_version_scans_only_the_latest_folder(self):
        for number in range(1, 6):
            self.version_dir(version=number)
        with mock.patch.object(
            PrevisFileStore, "_version", autospec=True, side_effect=PrevisFileStore._version
        ) as version:
            self.assertEqual(self.store.latest_version(100, 7).number, 5)
        self.assertEqual(version.call_count, 1)

    def test_latest_version_is_none_without_versions(self):
        make_dirs(self.root, "sequences", "0100", "a007")
        self.assertIsNone(self.store.latest_version(100, 7))


class CreationTests(StoreTestCase):
    def test_creating_an_existing_sequence_fails_and_changes_nothing(self):
        self.store.create_sequence(100)
        before = sorted(p.name for p in (self.root / "sequences").iterdir())
        with self.assertRaises(AlreadyExistsError):
            self.store.create_sequence(100)
        after = sorted(p.name for p in (self.root / "sequences").iterdir())
        self.assertEqual(before, after)

    def test_next_free_sequence_is_next_multiple_of_100(self):
        self.store.create_sequence(100)
        self.assertEqual(self.store.create_sequence().number, 200)
        self.store.create_sequence(350)
        self.assertEqual(self.store.create_sequence().number, 400)

    def test_next_free_numbers_when_empty(self):
        self.assertEqual(self.store.create_sequence().number, 0)
        self.assertEqual(self.store.create_sequence().number, 100)
        self.assertEqual(self.store.create_action(0).number, 0)
        self.assertEqual(self.store.create_action(0).number, 1)

    def test_next_free_action_follows_gaps(self):
        self.store.create_sequence(100)
        self.store.create_action(100, 5)
        self.assertEqual(self.store.create_action(100).number, 6)

    def test_out_of_range_numbers_are_rejected(self):
        self.store.create_sequence(0)
        for call in (
            lambda: self.store.create_sequence(10000),
            lambda: self.store.create_sequence(-1),
            lambda: self.store.create_action(0, 1000),
        ):
            with self.assertRaises(NumberOutOfRangeError):
                call()

    def test_next_free_past_maximum_fails(self):
        self.store.create_sequence(9900)
        with self.assertRaises(NumberOutOfRangeError):
            self.store.create_sequence()
        self.store.create_action(9900, 999)
        with self.assertRaises(NumberOutOfRangeError):
            self.store.create_action(9900)
        make_dirs(self.root, "sequences", "9900", "a999", "v999")
        with self.assertRaises(NumberOutOfRangeError):
            self.store.allocate_version(9900, 999, "ma")

    def test_creating_action_under_missing_sequence_fails_without_folder(self):
        make_dirs(self.root, "sequences")
        with self.assertRaises(NotFoundError):
            self.store.create_action(300, 0)
        self.assertEqual(list((self.root / "sequences").iterdir()), [])

    def test_first_sequence_creates_the_sequences_folder(self):
        self.assertFalse((self.root / "sequences").exists())
        self.store.create_sequence(0)
        self.assertTrue((self.root / "sequences" / "0000").is_dir())

    def test_missing_root_is_not_created(self):
        store = PrevisFileStore(self.root / "nope", SHOW)
        with self.assertRaises(NotFoundError):
            store.create_sequence(0)
        self.assertFalse((self.root / "nope").exists())

    def test_allocation_returns_scene_path_for_the_callers_extension(self):
        self.store.create_sequence(100)
        self.store.create_action(100, 7)
        path = self.store.allocate_version(100, 7, ".ma")
        expected = (
            self.root / "sequences" / "0100" / "a007" / "v001" / "abc_0100_a007_v001.ma"
        )
        self.assertEqual(path, expected)
        self.assertTrue(expected.parent.is_dir())
        self.assertFalse(expected.exists())
        self.assertEqual(
            self.store.allocate_version(100, 7, "mb").name, "abc_0100_a007_v002.mb"
        )

    def test_allocation_does_not_scan_existing_version_folders(self):
        for number in range(1, 6):
            self.version_dir(version=number)
        with mock.patch.object(PrevisFileStore, "_version", autospec=True) as version:
            self.assertEqual(
                self.store.allocate_version(100, 7, "ma").parent.name, "v006"
            )
        version.assert_not_called()

    def test_allocation_skips_gaps(self):
        self.version_dir(version=1)
        self.version_dir(version=3)
        self.assertEqual(
            self.store.allocate_version(100, 7, "ma").parent.name, "v004"
        )

    def test_allocation_does_not_reuse_a_version_without_scene_file(self):
        self.version_dir(version=1)
        self.version_dir(version=2)
        self.assertEqual(
            self.store.allocate_version(100, 7, "ma").parent.name, "v003"
        )

    def test_allocation_in_missing_action_fails(self):
        self.store.create_sequence(100)
        with self.assertRaises(NotFoundError):
            self.store.allocate_version(100, 7, "ma")

    def test_allocation_rejects_bad_extensions_without_creating_a_folder(self):
        self.store.create_sequence(100)
        self.store.create_action(100, 7)
        for bad in ("", ".", "ma/../x", None):
            with self.subTest(ext=bad):
                with self.assertRaises(InvalidNameError):
                    self.store.allocate_version(100, 7, bad)
        self.assertEqual(self.store.list_versions(100, 7), [])

    def test_store_rejects_a_bad_show_code(self):
        for bad in ("../x", "a b", ""):
            with self.subTest(show=bad):
                with self.assertRaises(InvalidNameError):
                    PrevisFileStore(self.root, bad)

    def _lose_first_race(self):
        """Make the first folder creation fail as if another process won it."""
        real_mkdir = PrevisFileStore._mkdir
        calls = []

        def mkdir(path):
            calls.append(path)
            if len(calls) == 1:
                raise AlreadyExistsError(f"Already exists: {path}")
            real_mkdir(path)

        return mock.patch.object(PrevisFileStore, "_mkdir", staticmethod(mkdir))

    def test_a_lost_race_moves_on_to_the_next_number(self):
        self.store.create_sequence(100)
        self.store.create_action(100, 7)
        with self._lose_first_race():
            self.assertEqual(
                self.store.allocate_version(100, 7, "ma").parent.name, "v002"
            )
        with self._lose_first_race():
            self.assertEqual(self.store.create_action(100).number, 9)
        with self._lose_first_race():
            self.assertEqual(self.store.create_sequence().number, 300)

    def test_simultaneous_allocations_get_distinct_versions(self):
        self.store.create_sequence(100)
        self.store.create_action(100, 7)
        with ThreadPoolExecutor(max_workers=20) as pool:
            paths = list(
                pool.map(lambda _: self.store.allocate_version(100, 7, "ma"), range(20))
            )
        self.assertEqual(len({p.parent.name for p in paths}), 20)
        self.assertEqual(
            [v.number for v in self.store.list_versions(100, 7)], list(range(1, 21))
        )

    def test_simultaneous_next_free_actions_get_distinct_numbers(self):
        self.store.create_sequence(100)
        with ThreadPoolExecutor(max_workers=10) as pool:
            numbers = list(
                pool.map(lambda _: self.store.create_action(100).number, range(10))
            )
        self.assertEqual(sorted(numbers), list(range(10)))


if __name__ == "__main__":
    unittest.main()
