"""Tests for the settings file lock and for sessions that set settings at the same time."""
import os
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from mise_stage.backends.user_settings import (  # noqa: E402
    SettingDefinition,
    SettingsWriteError,
    UserSettings,
    lock,
    store,
)

THREADS = 8
ROUNDS = 25
COUNTERS = tuple(SettingDefinition(f"COUNTER_{i}", "Counters", 0) for i in range(THREADS))


class ConcurrentSetTests(unittest.TestCase):
    def setUp(self) -> None:
        store._reset_session_state()
        self.addCleanup(store._reset_session_state)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)

    def test_sessions_setting_different_settings_at_once_lose_nothing(self) -> None:
        def session(index: int) -> None:
            settings = UserSettings(self.directory, COUNTERS)
            for round_number in range(1, ROUNDS + 1):
                settings.set(f"COUNTER_{index}", round_number)

        with ThreadPoolExecutor(max_workers=THREADS) as pool:
            for future in [pool.submit(session, i) for i in range(THREADS)]:
                future.result()

        reader = UserSettings(self.directory, COUNTERS)
        self.assertEqual([reader.get(f"COUNTER_{i}") for i in range(THREADS)], [ROUNDS] * THREADS)

    def test_a_group_reset_and_a_set_outside_the_group_at_once_keep_both_effects(self) -> None:
        groups = (
            SettingDefinition("IN_GROUP", "First", 0),
            SettingDefinition("OUTSIDE", "Second", 0),
        )
        UserSettings(self.directory, groups).set("IN_GROUP", 1)

        def resetter() -> None:
            settings = UserSettings(self.directory, groups)
            for _ in range(ROUNDS):
                settings.set("IN_GROUP", 9)
                settings.reset_group("First")

        def setter() -> None:
            settings = UserSettings(self.directory, groups)
            for number in range(1, ROUNDS + 1):
                settings.set("OUTSIDE", number)

        with ThreadPoolExecutor(max_workers=2) as pool:
            for future in [pool.submit(resetter), pool.submit(setter)]:
                future.result()

        reader = UserSettings(self.directory, groups)
        self.assertEqual(reader.get("OUTSIDE"), ROUNDS)
        self.assertEqual(reader.get("IN_GROUP"), 0)

    def test_a_reader_never_sees_a_half_written_file_while_another_session_saves(self) -> None:
        writer = UserSettings(self.directory, COUNTERS)
        reader = UserSettings(self.directory, COUNTERS)
        writer.set("COUNTER_0", 1)
        stop = threading.Event()
        seen: list[object] = []

        def read_in_a_loop() -> None:
            while not stop.is_set():
                seen.append(reader.get("COUNTER_0"))

        with self.assertNoLogs(store.log, "WARNING"):
            thread = threading.Thread(target=read_in_a_loop)
            thread.start()
            try:
                for number in range(2, 60):
                    writer.set("COUNTER_0", number)
                    writer.set("COUNTER_1", number)
            finally:
                stop.set()
                thread.join()

        self.assertTrue(seen)
        self.assertNotIn(0, seen, "a read took a half-written file for an unreadable one and fell back to the default")


class LockTests(unittest.TestCase):
    def setUp(self) -> None:
        store._reset_session_state()
        self.addCleanup(store._reset_session_state)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)
        self.path = self.directory / store.FILE_NAME
        self.lock_path = self.directory / "user_settings.yaml.lock"
        self.settings = UserSettings(self.directory, COUNTERS)

    def names(self) -> list[str]:
        return sorted(p.name for p in self.directory.iterdir())

    def test_a_second_session_cannot_take_a_held_lock(self) -> None:
        with lock.FileLock(self.lock_path), mock.patch.object(lock, "LOCK_WAIT", 0.1):
            with self.assertRaises(SettingsWriteError):
                with lock.FileLock(self.lock_path):
                    self.fail("the lock was taken twice")
        self.assertFalse(self.lock_path.exists())

    def test_a_set_gives_up_when_another_session_holds_the_lock_and_changes_nothing(self) -> None:
        self.settings.set("COUNTER_0", 1)
        before = self.path.read_text(encoding="utf-8")
        self.lock_path.write_text("", encoding="utf-8")
        with mock.patch.object(lock, "LOCK_WAIT", 0.1), self.assertRaises(SettingsWriteError) as raised:
            self.settings.set("COUNTER_1", 2)
        self.assertIn("user_settings.yaml.lock", str(raised.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertTrue(self.lock_path.exists(), "a lock this session never took must be left alone")
        self.assertEqual(self.settings.get("COUNTER_1"), 2, "the value of a save that timed out is held")

    def test_a_folder_that_denies_the_lock_file_fails_fast_with_the_real_cause(self) -> None:
        with (
            mock.patch.object(lock, "LOCK_WAIT", 30.0),
            mock.patch.object(lock.os, "open", side_effect=PermissionError("Permission denied")),
            mock.patch.object(lock.time, "sleep"),
            self.assertRaises(SettingsWriteError) as raised,
        ):
            self.settings.set("COUNTER_0", 4)
        self.assertIn("denied", str(raised.exception))
        self.assertNotIn("another session", str(raised.exception))

    def test_a_stale_lock_that_cannot_be_removed_times_out_instead_of_spinning(self) -> None:
        self.lock_path.write_text("", encoding="utf-8")
        long_ago = time.time() - 3600
        os.utime(self.lock_path, (long_ago, long_ago))
        started = time.monotonic()
        with (
            mock.patch.object(lock, "LOCK_WAIT", 0.2),
            mock.patch.object(lock.os, "unlink", side_effect=PermissionError("held")),
            self.assertRaises(SettingsWriteError) as raised,
        ):
            self.settings.set("COUNTER_0", 4)
        self.assertIn("another session", str(raised.exception))
        self.assertLess(time.monotonic() - started, 5.0)

    def test_releasing_the_lock_retries_when_the_file_is_briefly_busy(self) -> None:
        real_unlink = os.unlink
        calls: list[int] = []

        def busy_once(path: str | os.PathLike[str]) -> None:
            calls.append(1)
            if len(calls) == 1:
                raise PermissionError("busy")
            real_unlink(path)

        with mock.patch.object(lock.os, "unlink", busy_once), mock.patch.object(lock.time, "sleep"):
            with lock.FileLock(self.lock_path):
                self.assertTrue(self.lock_path.exists())
        self.assertFalse(self.lock_path.exists())
        self.assertEqual(len(calls), 2)

    def test_a_lock_file_that_will_not_go_is_left_with_a_warning(self) -> None:
        with (
            mock.patch.object(lock.os, "unlink", side_effect=PermissionError("held")),
            mock.patch.object(lock.time, "sleep"),
            self.assertLogs(lock.log, "WARNING"),
        ):
            with lock.FileLock(self.lock_path):
                pass
        self.assertTrue(self.lock_path.exists())

    def test_releasing_a_lock_that_is_already_gone_is_quiet(self) -> None:
        with self.assertNoLogs(lock.log, "WARNING"):
            with lock.FileLock(self.lock_path):
                self.lock_path.unlink()

    def test_a_lock_left_by_a_crashed_session_is_cleared(self) -> None:
        self.lock_path.write_text("", encoding="utf-8")
        long_ago = time.time() - 3600
        os.utime(self.lock_path, (long_ago, long_ago))
        self.settings.set("COUNTER_0", 4)
        self.assertEqual(self.settings.get("COUNTER_0"), 4)
        self.assertEqual(self.names(), ["user_settings.yaml"])

    def test_no_lock_or_temporary_file_remains_after_a_good_save(self) -> None:
        self.settings.set("COUNTER_0", 4)
        self.assertEqual(self.names(), ["user_settings.yaml"])

    def test_no_lock_or_temporary_file_remains_after_a_failed_swap(self) -> None:
        self.settings.set("COUNTER_0", 4)
        with (
            mock.patch.object(store.os, "replace", side_effect=PermissionError("denied")),
            mock.patch.object(store.time, "sleep"),
            self.assertRaises(SettingsWriteError),
        ):
            self.settings.set("COUNTER_0", 5)
        self.assertEqual(self.names(), ["user_settings.yaml"])


if __name__ == "__main__":
    unittest.main()
