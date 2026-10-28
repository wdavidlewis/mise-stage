"""Tests for finding and reading the user settings file."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from mise_stage.backends.user_settings import (  # noqa: E402
    SettingDefinition,
    UnknownSettingError,
    UserSettings,
    default_directory,
    store,
)

LOGGER = "mise_stage.backends.user_settings.store"
ENABLED = SettingDefinition("ENABLED", "Display", True)
COUNT = SettingDefinition("COUNT", "Display", 3)
LEVEL = SettingDefinition("LEVEL", "Quality", "low", ("low", "high"))
DEFINITIONS = (ENABLED, COUNT, LEVEL)


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


if __name__ == "__main__":
    unittest.main()
