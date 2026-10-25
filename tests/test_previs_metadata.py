import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from utils.previs_files import MetadataError, NotFoundError, PrevisFileStore  # noqa: E402
from utils.previs_files import metadata  # noqa: E402

COMMENT = "Caméra déplacée — 新しい\nsecond line 🎬\r\nthird"


class StoreCommentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.store = PrevisFileStore(self.root, "abc")
        self.store.create_sequence(100)
        self.store.create_action(100, 7)
        self.store.allocate_version(100, 7, "ma")
        self.action_dir = self.root / "sequences" / "0100" / "a007"
        self.version_dir = self.action_dir / "v001"

    def test_unicode_comment_round_trips_for_action_and_version(self):
        self.store.set_action_comment(100, 7, COMMENT)
        self.store.set_version_comment(100, 7, 1, COMMENT)
        self.assertEqual(self.store.get_action_comment(100, 7), COMMENT)
        self.assertEqual(self.store.get_version_comment(100, 7, 1), COMMENT)

    def test_comment_is_stored_as_utf8_without_escapes(self):
        self.store.set_version_comment(100, 7, 1, "Caméra — 新しい")
        raw = (self.version_dir / "meta.json").read_bytes()
        self.assertIn("Caméra — 新しい".encode("utf-8"), raw)
        self.assertNotIn(b"\\u", raw)

    def test_missing_comment_reads_as_empty(self):
        self.assertEqual(self.store.get_action_comment(100, 7), "")
        self.assertEqual(self.store.get_version_comment(100, 7, 1), "")

    def test_setting_twice_keeps_the_second(self):
        self.store.set_action_comment(100, 7, "first")
        self.store.set_action_comment(100, 7, "second")
        self.assertEqual(self.store.get_action_comment(100, 7), "second")

    def test_no_temporary_file_is_left_behind(self):
        self.store.set_version_comment(100, 7, 1, "hello")
        self.assertEqual(
            sorted(p.name for p in self.version_dir.iterdir()), ["meta.json"]
        )

    def test_metadata_file_is_not_a_scene_file(self):
        self.store.set_version_comment(100, 7, 1, "hello")
        self.assertEqual(self.store.list_versions(100, 7)[0].scene_files, ())

    def test_comment_on_missing_action_or_version_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.store.set_action_comment(100, 8, "x")
        with self.assertRaises(NotFoundError):
            self.store.get_version_comment(100, 7, 2)
        with self.assertRaises(NotFoundError):
            self.store.set_version_comment(300, 7, 1, "x")

    def test_simultaneous_writes_leave_one_complete_comment(self):
        comments = [f"comment {n} — é" for n in range(10)]
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda c: self.store.set_action_comment(100, 7, c), comments))
        self.assertIn(self.store.get_action_comment(100, 7), comments)
        self.assertEqual(
            sorted(p.name for p in self.action_dir.iterdir()), ["meta.json", "v001"]
        )


class MetadataFileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.folder = Path(self._tmp.name)
        self.path = self.folder / "meta.json"

    def test_reads_a_file_with_a_byte_order_mark(self):
        self.path.write_bytes(
            b"\xef\xbb\xbf" + json.dumps({"comment": "héllo"}).encode("utf-8")
        )
        self.assertEqual(metadata.read_comment(self.folder), "héllo")

    def test_invalid_json_raises_and_names_the_file(self):
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(MetadataError) as ctx:
            metadata.read_comment(self.folder)
        self.assertIn("meta.json", str(ctx.exception))

    def test_wrong_shapes_raise(self):
        for text in ('["a"]', '{"comment": 5}'):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertRaises(MetadataError):
                    metadata.read_comment(self.folder)

    def test_writing_over_invalid_json_raises_and_keeps_the_file(self):
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(MetadataError):
            metadata.write_comment(self.folder, "x")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{not json")

    def test_other_keys_survive_a_comment_write(self):
        self.path.write_text(json.dumps({"comment": "old", "owner": "sam"}))
        metadata.write_comment(self.folder, "new")
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8")),
            {"comment": "new", "owner": "sam"},
        )

    def test_replace_is_retried_when_windows_reports_a_sharing_violation(self):
        real_replace = metadata.os.replace
        attempts = []

        def flaky_replace(src, dst):
            attempts.append(src)
            if len(attempts) <= 2:
                raise PermissionError("in use")
            real_replace(src, dst)

        with mock.patch.object(metadata.os, "replace", flaky_replace), mock.patch.object(
            metadata.time, "sleep"
        ):
            metadata.write_comment(self.folder, "hello")
        self.assertEqual(len(attempts), 3)
        self.assertEqual(metadata.read_comment(self.folder), "hello")

    def test_a_replace_that_never_succeeds_raises_and_leaves_no_temporary_file(self):
        with mock.patch.object(
            metadata.os, "replace", side_effect=PermissionError("in use")
        ), mock.patch.object(metadata.time, "sleep"):
            with self.assertRaises(PermissionError):
                metadata.write_comment(self.folder, "hello")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_non_string_comment_is_rejected(self):
        with self.assertRaises(TypeError):
            metadata.write_comment(self.folder, None)


if __name__ == "__main__":
    unittest.main()
