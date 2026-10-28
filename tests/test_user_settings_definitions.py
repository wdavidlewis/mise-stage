"""Tests for user setting declarations, value checks and the shipped settings."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from mise_stage.backends.user_settings import (  # noqa: E402
    AUTO_OPEN_CAMERA_MONITOR,
    CONFIRM_CAMERA_DELETE,
    USER_SETTINGS,
    InvalidValueError,
    SettingDefinition,
    UserSettingsError,
    validate_definitions,
)


def _definition(default: object, choices: tuple[str, ...] | None = None) -> SettingDefinition:
    return SettingDefinition("KEY", "Group", default, choices)  # type: ignore[arg-type]


class ValueCheckTests(unittest.TestCase):
    def test_on_off_setting_accepts_booleans_only(self) -> None:
        setting = _definition(True)
        self.assertIs(setting.validate(False), False)
        self.assertIs(setting.validate(True), True)
        for bad in (1, 0, "yes", None, 1.0):
            with self.subTest(bad=bad), self.assertRaises(InvalidValueError):
                setting.validate(bad)

    def test_whole_number_setting_rejects_booleans_and_fractions(self) -> None:
        setting = _definition(5)
        self.assertEqual(setting.validate(3), 3)
        for bad in (True, 3.5, "3"):
            with self.subTest(bad=bad), self.assertRaises(InvalidValueError):
                setting.validate(bad)

    def test_number_setting_accepts_ints_and_floats_but_not_booleans_or_text(self) -> None:
        setting = _definition(1.5)
        self.assertEqual(setting.validate(3), 3)
        self.assertEqual(setting.validate(3.5), 3.5)
        for bad in ("3", True):
            with self.subTest(bad=bad), self.assertRaises(InvalidValueError):
                setting.validate(bad)

    def test_text_setting_accepts_any_string_including_empty(self) -> None:
        setting = _definition("abc")
        self.assertEqual(setting.validate(""), "")
        self.assertEqual(setting.validate("abc"), "abc")
        with self.assertRaises(InvalidValueError):
            setting.validate(5)

    def test_choice_setting_accepts_listed_values_only(self) -> None:
        setting = _definition("low", ("low", "high"))
        self.assertEqual(setting.validate("high"), "high")
        for bad in ("medium", "", 3, None):
            with self.subTest(bad=bad), self.assertRaises(InvalidValueError):
                setting.validate(bad)

    def test_invalid_value_error_is_a_user_settings_error(self) -> None:
        with self.assertRaises(UserSettingsError):
            _definition(True).validate("x")


class DeclarationTests(unittest.TestCase):
    def test_default_outside_the_choices_raises(self) -> None:
        with self.assertRaises(ValueError):
            _definition("medium", ("low", "high"))

    def test_choices_need_a_text_default_and_text_choices(self) -> None:
        with self.assertRaises(ValueError):
            _definition(1, ("1", "2"))
        with self.assertRaises(ValueError):
            _definition("a", ("a", 2))  # type: ignore[arg-type]

    def test_unsupported_default_type_raises(self) -> None:
        for bad in ([1], None, {"a": 1}, (1, 2)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                _definition(bad)

    def test_blank_key_or_group_raises(self) -> None:
        with self.assertRaises(ValueError):
            SettingDefinition("", "Group", True)
        with self.assertRaises(ValueError):
            SettingDefinition("KEY", "", True)

    def test_duplicate_keys_raise_when_declarations_are_built(self) -> None:
        first = SettingDefinition("KEY", "A", True)
        second = SettingDefinition("KEY", "B", False)
        with self.assertRaises(ValueError):
            validate_definitions([first, second])

    def test_validate_definitions_returns_the_declarations_as_a_tuple(self) -> None:
        first = SettingDefinition("ONE", "A", True)
        second = SettingDefinition("TWO", "A", 2)
        self.assertEqual(validate_definitions([first, second]), (first, second))


class ShippedSettingsTests(unittest.TestCase):
    def test_camera_manager_settings_are_declared_as_specified(self) -> None:
        by_key = {setting.key: setting for setting in USER_SETTINGS}
        self.assertEqual(set(by_key), {"CONFIRM_CAMERA_DELETE", "AUTO_OPEN_CAMERA_MONITOR"})

        confirm = by_key["CONFIRM_CAMERA_DELETE"]
        self.assertEqual((confirm.group, confirm.default, confirm.choices), ("Cameras", True, None))

        auto_open = by_key["AUTO_OPEN_CAMERA_MONITOR"]
        self.assertEqual((auto_open.group, auto_open.default, auto_open.choices), ("Camera Monitor", False, None))

    def test_key_constants_equal_their_own_names(self) -> None:
        self.assertEqual(CONFIRM_CAMERA_DELETE, "CONFIRM_CAMERA_DELETE")
        self.assertEqual(AUTO_OPEN_CAMERA_MONITOR, "AUTO_OPEN_CAMERA_MONITOR")

    def test_shipped_declarations_pass_the_declaration_check(self) -> None:
        self.assertEqual(validate_definitions(USER_SETTINGS), USER_SETTINGS)


if __name__ == "__main__":
    unittest.main()
