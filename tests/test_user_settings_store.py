"""Tests for finding and reading the user settings file."""
import contextlib
import os
import stat
import sys
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from mise_stage.backends.user_settings import (  # noqa: E402
    InvalidValueError,
    SettingDefinition,
    SettingsWriteError,
    UnknownGroupError,
    UnknownSettingError,
    UserSettings,
    default_directory,
    lock,
    store,
)

LOGGER = "mise_stage.backends.user_settings.store"
ENABLED = SettingDefinition("ENABLED", "Display", True)
COUNT = SettingDefinition("COUNT", "Display", 3)
LEVEL = SettingDefinition("LEVEL", "Quality", "low", ("low", "high"))
DEFINITIONS = (ENABLED, COUNT, LEVEL)


@contextlib.contextmanager
def failing_swap() -> Iterator[None]:
    """Make every swap of the settings file fail, as a file that stays busy would."""
    with (
        mock.patch.object(store.os, "replace", side_effect=PermissionError("denied")),
        mock.patch.object(store.time, "sleep"),
    ):
        yield


class SettingsFolderTests(unittest.TestCase):
    def test_windows_uses_appdata(self) -> None:
        with mock.patch.object(sys, "platform", "win32"), mock.patch.dict(os.environ, {"APPDATA": "C:/Roaming"}):
            self.assertEqual(default_directory(), Path("C:/Roaming") / "mise-stage")

    def test_macos_uses_application_support(self) -> None:
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(Path, "home", return_value=Path("/Users/a")):
            self.assertEqual(default_directory(), Path("/Users/a") / "Library" / "Application Support" / "mise-stage")

    def test_linux_prefers_xdg_config_home(self) -> None:
        with mock.patch.object(sys, "platform", "linux"), mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "/cfg"}):
            self.assertEqual(default_directory(), Path("/cfg") / "mise-stage")

    def test_linux_falls_back_to_dot_config(self) -> None:
        with (
            mock.patch.object(sys, "platform", "linux"),
            mock.patch.dict(os.environ, clear=True),
            mock.patch.object(Path, "home", return_value=Path("/home/a")),
        ):
            self.assertEqual(default_directory(), Path("/home/a") / ".config" / "mise-stage")


class ReadTests(unittest.TestCase):
    def setUp(self) -> None:
        store._reset_session_state()
        self.addCleanup(store._reset_session_state)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name)
        self.path = self.directory / store.FILE_NAME
        self.settings = UserSettings(self.directory, DEFINITIONS)

    def write_file(self, text: str) -> None:
        self.path.write_text(text, encoding="utf-8")

    def test_the_file_is_user_settings_yaml_in_the_given_folder(self) -> None:
        self.assertEqual(self.settings.path, self.directory / "user_settings.yaml")

    def test_with_no_file_a_read_returns_the_default_and_logs_nothing(self) -> None:
        with self.assertNoLogs(LOGGER, "WARNING"):
            self.assertIs(self.settings.get("ENABLED"), True)
            self.assertEqual(self.settings.get("LEVEL"), "low")

    def test_an_empty_file_reads_as_defaults_without_a_warning(self) -> None:
        self.write_file("")
        with self.assertNoLogs(LOGGER, "WARNING"):
            self.assertEqual(self.settings.get("COUNT"), 3)

    def test_a_valid_file_value_is_returned(self) -> None:
        self.write_file("ENABLED: false\nCOUNT: 7\nLEVEL: high\n")
        self.assertIs(self.settings.get("ENABLED"), False)
        self.assertEqual(self.settings.get("COUNT"), 7)
        self.assertEqual(self.settings.get("LEVEL"), "high")

    def test_a_wrong_kind_returns_the_default_and_warns_once(self) -> None:
        self.write_file("ENABLED: maybe\n")
        with self.assertLogs(LOGGER, "WARNING") as logs:
            self.assertIs(self.settings.get("ENABLED"), True)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("ENABLED", logs.output[0])
        with self.assertNoLogs(LOGGER, "WARNING"):
            self.assertIs(self.settings.get("ENABLED"), True)

    def test_an_out_of_list_choice_returns_the_default_and_warns(self) -> None:
        self.write_file("LEVEL: medium\n")
        with self.assertLogs(LOGGER, "WARNING"):
            self.assertEqual(self.settings.get("LEVEL"), "low")

    def test_a_syntax_error_returns_defaults_warns_once_and_leaves_the_file(self) -> None:
        text = "ENABLED: [unclosed\n"
        self.write_file(text)
        with self.assertLogs(LOGGER, "WARNING") as logs:
            self.assertIs(self.settings.get("ENABLED"), True)
            self.assertEqual(self.settings.get("COUNT"), 3)
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_a_file_that_is_not_utf8_text_returns_defaults_and_warns_once(self) -> None:
        self.path.write_bytes("COUNT: 5\n".encode("utf-16"))
        with self.assertLogs(LOGGER, "WARNING") as logs:
            self.assertEqual(self.settings.get("COUNT"), 3)
            self.assertEqual(self.settings.get("ENABLED"), True)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("UTF-8", logs.output[0])

    def test_yaml_that_is_not_a_mapping_returns_defaults_and_warns(self) -> None:
        self.write_file("- ENABLED\n- COUNT\n")
        with self.assertLogs(LOGGER, "WARNING"):
            self.assertEqual(self.settings.get("COUNT"), 3)

    def test_a_bad_value_does_not_hide_the_valid_ones(self) -> None:
        self.write_file("ENABLED: maybe\nCOUNT: 9\n")
        with self.assertLogs(LOGGER, "WARNING"):
            self.assertIs(self.settings.get("ENABLED"), True)
        self.assertEqual(self.settings.get("COUNT"), 9)

    def test_an_unknown_key_warns_once_changes_nothing_and_stays_in_the_file(self) -> None:
        text = "RETIRED_SETTING: 4\nCOUNT: 9\n"
        self.write_file(text)
        with self.assertLogs(LOGGER, "WARNING") as logs:
            self.assertEqual(self.settings.get("COUNT"), 9)
            self.assertEqual(self.settings.get("COUNT"), 9)
        self.assertEqual(len(logs.records), 1)
        self.assertIn("RETIRED_SETTING", logs.output[0])
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_reading_an_undeclared_setting_raises(self) -> None:
        with self.assertRaises(UnknownSettingError):
            self.settings.get("NOT_DECLARED")

    def test_a_change_made_by_another_store_object_is_seen_without_a_restart(self) -> None:
        other = UserSettings(self.directory, DEFINITIONS)
        self.assertEqual(self.settings.get("COUNT"), 3)
        self.write_file("COUNT: 8\n")
        self.assertEqual(other.get("COUNT"), 8)
        self.assertEqual(self.settings.get("COUNT"), 8)
        self.write_file("COUNT: 9\n")
        self.assertEqual(self.settings.get("COUNT"), 9)

    def test_a_read_retries_when_the_file_is_briefly_busy(self) -> None:
        self.write_file("COUNT: 5\n")
        real_read_text = Path.read_text
        calls: list[int] = []

        def busy_once(path: Path, *args: object, **kwargs: object) -> str:
            calls.append(1)
            if len(calls) == 1:
                raise PermissionError("busy")
            return real_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch.object(Path, "read_text", busy_once), mock.patch.object(store.time, "sleep"):
            self.assertEqual(self.settings.get("COUNT"), 5)
        self.assertEqual(len(calls), 2)

    def test_a_file_that_stays_unreadable_returns_defaults_and_warns(self) -> None:
        self.write_file("COUNT: 5\n")
        with (
            mock.patch.object(Path, "read_text", side_effect=PermissionError("busy")),
            mock.patch.object(store.time, "sleep"),
            self.assertLogs(LOGGER, "WARNING"),
        ):
            self.assertEqual(self.settings.get("COUNT"), 3)


class SetTests(unittest.TestCase):
    def setUp(self) -> None:
        store._reset_session_state()
        self.addCleanup(store._reset_session_state)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name) / "profile"
        self.path = self.directory / store.FILE_NAME
        self.settings = UserSettings(self.directory, DEFINITIONS)

    def leftovers(self) -> list[str]:
        return sorted(p.name for p in self.directory.iterdir() if p.name != store.FILE_NAME)

    def test_setting_the_default_with_no_file_creates_nothing(self) -> None:
        self.settings.set("COUNT", 3)
        self.settings.set("ENABLED", True)
        self.assertFalse(self.directory.exists())

    def test_setting_a_different_value_creates_the_folder_and_the_file(self) -> None:
        self.settings.set("COUNT", 3)
        self.settings.set("COUNT", 5)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "COUNT: 5\n")
        self.assertEqual(self.settings.get("COUNT"), 5)

    def test_setting_back_to_the_default_keeps_the_file_and_other_keys(self) -> None:
        self.settings.set("COUNT", 5)
        self.settings.set("LEVEL", "high")
        self.settings.set("COUNT", 3)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "COUNT: 3\nLEVEL: high\n")

    def test_a_deeply_missing_folder_is_created(self) -> None:
        deep = UserSettings(self.directory / "a" / "b" / "c", DEFINITIONS)
        deep.set("COUNT", 4)
        self.assertEqual(deep.get("COUNT"), 4)

    def test_a_wrong_kind_raises_and_writes_nothing(self) -> None:
        for key, bad in (("ENABLED", "yes"), ("COUNT", True), ("COUNT", 2.5), ("LEVEL", "medium")):
            with self.subTest(key=key, bad=bad), self.assertRaises(InvalidValueError):
                self.settings.set(key, bad)
        self.assertFalse(self.directory.exists())

    def test_setting_an_undeclared_key_raises(self) -> None:
        with self.assertRaises(UnknownSettingError):
            self.settings.set("NOT_DECLARED", 1)

    def test_a_choice_setting_stores_a_listed_value(self) -> None:
        self.settings.set("LEVEL", "high")
        self.assertEqual(self.settings.get("LEVEL"), "high")

    def test_a_number_setting_stores_a_float(self) -> None:
        ratio = UserSettings(self.directory, [SettingDefinition("RATIO", "Display", 1.5)])
        ratio.set("RATIO", 2.25)
        self.assertEqual(ratio.get("RATIO"), 2.25)

    def test_unknown_keys_survive_a_set_and_comments_do_not(self) -> None:
        self.directory.mkdir()
        self.path.write_text("# my notes\nRETIRED_SETTING: 4\nCOUNT: 2\n", encoding="utf-8")
        self.settings.set("COUNT", 9)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("RETIRED_SETTING: 4", text)
        self.assertIn("COUNT: 9", text)
        self.assertNotIn("my notes", text)

    def test_a_file_with_a_syntax_error_is_kept_as_invalid_and_replaced(self) -> None:
        self.directory.mkdir()
        broken = "COUNT: [unclosed\n"
        self.path.write_text(broken, encoding="utf-8")
        invalid = self.directory / "user_settings.yaml.invalid"
        invalid.write_text("older", encoding="utf-8")
        self.settings.set("LEVEL", "high")
        self.assertEqual(invalid.read_text(encoding="utf-8"), broken)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "LEVEL: high\n")

    def test_a_file_that_is_not_utf8_text_is_kept_as_invalid_by_a_set(self) -> None:
        self.directory.mkdir()
        raw = "COUNT: 5\n".encode("utf-16")
        self.path.write_bytes(raw)
        self.settings.set("LEVEL", "high")
        self.assertEqual((self.directory / "user_settings.yaml.invalid").read_bytes(), raw)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "LEVEL: high\n")

    def test_yaml_that_is_not_a_mapping_is_kept_as_invalid_by_a_set(self) -> None:
        self.directory.mkdir()
        self.path.write_text("- COUNT\n- LEVEL\n", encoding="utf-8")
        self.settings.set("COUNT", 4)
        self.assertEqual((self.directory / "user_settings.yaml.invalid").read_text(encoding="utf-8"), "- COUNT\n- LEVEL\n")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "COUNT: 4\n")

    def test_a_read_only_settings_file_raises_and_is_left_alone(self) -> None:
        self.settings.set("COUNT", 5)
        self.path.chmod(stat.S_IREAD)
        self.addCleanup(self.path.chmod, stat.S_IREAD | stat.S_IWRITE)
        with self.assertRaises(SettingsWriteError) as raised:
            self.settings.set("COUNT", 7)
        self.assertIn("read-only", str(raised.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "COUNT: 5\n")
        self.assertEqual(self.settings.get("COUNT"), 7)
        self.assertEqual(self.leftovers(), [])

    def test_a_failed_save_raises_names_the_file_holds_the_value_and_leaves_no_litter(self) -> None:
        self.settings.set("COUNT", 5)
        with failing_swap(), self.assertRaises(SettingsWriteError) as raised:
            self.settings.set("COUNT", 7)
        self.assertIn(store.FILE_NAME, str(raised.exception))
        self.assertEqual(self.settings.get("COUNT"), 7)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "COUNT: 5\n")
        self.assertEqual(self.leftovers(), [])

    def test_the_next_good_save_writes_the_value_and_reads_follow_the_file_again(self) -> None:
        with failing_swap(), self.assertRaises(SettingsWriteError):
            self.settings.set("COUNT", 7)
        self.settings.set("COUNT", 8)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "COUNT: 8\n")
        self.path.write_text("COUNT: 11\n", encoding="utf-8")
        self.assertEqual(self.settings.get("COUNT"), 11)

    def test_a_folder_that_cannot_be_created_raises_and_holds_the_value(self) -> None:
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            with self.assertRaises(SettingsWriteError):
                self.settings.set("COUNT", 7)
        self.assertEqual(self.settings.get("COUNT"), 7)

    def test_a_held_value_is_not_returned_for_a_different_folder(self) -> None:
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            with self.assertRaises(SettingsWriteError):
                self.settings.set("COUNT", 7)
        other = UserSettings(Path(self._tmp.name) / "other", DEFINITIONS)
        self.assertEqual(other.get("COUNT"), 3)

    def test_setting_the_default_with_no_file_drops_a_value_held_from_a_failed_save(self) -> None:
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            with self.assertRaises(SettingsWriteError):
                self.settings.set("COUNT", 7)
        self.settings.set("COUNT", 3)
        self.assertEqual(self.settings.get("COUNT"), 3)
        self.assertFalse(self.directory.exists())


class ResetTests(unittest.TestCase):
    def setUp(self) -> None:
        store._reset_session_state()
        self.addCleanup(store._reset_session_state)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.directory = Path(self._tmp.name) / "profile"
        self.path = self.directory / store.FILE_NAME
        self.settings = UserSettings(self.directory, DEFINITIONS)

    def test_resetting_a_group_returns_its_settings_to_defaults_and_leaves_other_groups(self) -> None:
        self.settings.set("COUNT", 5)
        self.settings.set("ENABLED", False)
        self.settings.set("LEVEL", "high")
        self.settings.reset_group("Display")
        self.assertEqual(self.settings.get("COUNT"), 3)
        self.assertIs(self.settings.get("ENABLED"), True)
        self.assertEqual(self.settings.get("LEVEL"), "high")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "LEVEL: high\n")

    def test_resetting_all_returns_every_setting_to_its_default_and_keeps_the_file(self) -> None:
        self.settings.set("COUNT", 5)
        self.settings.set("LEVEL", "high")
        self.settings.reset_all()
        self.assertEqual(self.settings.get("COUNT"), 3)
        self.assertEqual(self.settings.get("LEVEL"), "low")
        self.assertTrue(self.path.exists())
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), [store.FILE_NAME])

    def test_resetting_with_no_file_creates_no_file_or_folder(self) -> None:
        self.settings.reset_group("Display")
        self.settings.reset_all()
        self.assertFalse(self.directory.exists())

    def test_a_file_holding_none_of_the_keys_is_left_exactly_as_it_was(self) -> None:
        self.directory.mkdir()
        text = "# kept\nLEVEL: high\n"
        self.path.write_text(text, encoding="utf-8")
        self.settings.reset_group("Display")
        self.assertEqual(self.path.read_text(encoding="utf-8"), text)

    def test_resetting_an_undeclared_group_raises(self) -> None:
        with self.assertRaises(UnknownGroupError):
            self.settings.reset_group("Nope")

    def test_unknown_keys_survive_a_reset(self) -> None:
        self.directory.mkdir()
        self.path.write_text("RETIRED_SETTING: 4\nCOUNT: 2\n", encoding="utf-8")
        self.settings.reset_all()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "RETIRED_SETTING: 4\n")

    def test_a_reset_drops_a_value_held_from_a_failed_save(self) -> None:
        self.settings.set("COUNT", 5)
        with failing_swap(), self.assertRaises(SettingsWriteError):
            self.settings.set("COUNT", 7)
        self.assertEqual(self.settings.get("COUNT"), 7)
        self.settings.reset_group("Display")
        self.assertEqual(self.settings.get("COUNT"), 3)

    def test_a_reset_drops_a_held_value_even_when_there_is_no_file(self) -> None:
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("denied")):
            with self.assertRaises(SettingsWriteError):
                self.settings.set("COUNT", 7)
        self.settings.reset_all()
        self.assertEqual(self.settings.get("COUNT"), 3)

    def test_a_failed_reset_keeps_the_value_held_from_a_failed_save(self) -> None:
        self.settings.set("COUNT", 5)
        with failing_swap(), self.assertRaises(SettingsWriteError):
            self.settings.set("COUNT", 7)
        lock_path = self.directory / "user_settings.yaml.lock"
        lock_path.write_text("", encoding="utf-8")
        with mock.patch.object(lock, "LOCK_WAIT", 0.1), self.assertRaises(SettingsWriteError):
            self.settings.reset_group("Display")
        self.assertEqual(self.settings.get("COUNT"), 7)
        lock_path.unlink()
        self.settings.reset_group("Display")
        self.assertEqual(self.settings.get("COUNT"), 3)

    def test_a_file_that_is_not_utf8_text_is_left_in_place_by_a_reset(self) -> None:
        self.directory.mkdir()
        raw = "COUNT: 5\n".encode("utf-16")
        self.path.write_bytes(raw)
        self.settings.reset_all()
        self.assertEqual(self.path.read_bytes(), raw)

    def test_a_file_with_a_syntax_error_is_left_in_place_by_a_reset(self) -> None:
        self.directory.mkdir()
        broken = "COUNT: [unclosed\n"
        self.path.write_text(broken, encoding="utf-8")
        self.settings.reset_all()
        self.assertEqual(self.path.read_text(encoding="utf-8"), broken)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), [store.FILE_NAME])

    def test_a_reset_gives_up_when_another_session_holds_the_lock_and_changes_nothing(self) -> None:
        self.settings.set("COUNT", 5)
        before = self.path.read_text(encoding="utf-8")
        (self.directory / "user_settings.yaml.lock").write_text("", encoding="utf-8")
        with mock.patch.object(lock, "LOCK_WAIT", 0.1), self.assertRaises(SettingsWriteError):
            self.settings.reset_group("Display")
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
