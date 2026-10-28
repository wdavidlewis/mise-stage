"""Declarations of the user settings: key, group, default and allowed values.

A setting's kind comes from the type of its default: on/off (bool), whole
number (int), number (float) or text (str). A text setting with a list of
choices holds one of them. Each setting is addressed by its key alone, and a
key is unique across all groups.
"""
from collections.abc import Iterable
from dataclasses import dataclass

from .errors import InvalidValueError

SettingValue = bool | int | float | str

CONFIRM_CAMERA_DELETE = "CONFIRM_CAMERA_DELETE"
AUTO_OPEN_CAMERA_MONITOR = "AUTO_OPEN_CAMERA_MONITOR"

_KINDS = (bool, int, float, str)


@dataclass(frozen=True)
class SettingDefinition:
    """One declared user setting.

    Attributes:
        key: The setting's name, unique across all user settings.
        group: The group the setting belongs to, such as "Cameras".
        default: The value used when the file or the key is missing. Its type
            decides what the setting can hold.
        choices: For a text setting, the values it may hold, which include the
            default. None for a setting that is not a choice.

    Raises:
        ValueError: If the key or group is blank, the default is not an
            on/off, whole number, number or text value, or the choices are not
            all text and do not include a text default.
    """

    key: str
    group: str
    default: SettingValue
    choices: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.key or not self.group:
            raise ValueError("A setting needs a key and a group")
        if type(self.default) not in _KINDS:
            raise ValueError(f"{self.key}: the default must be on/off, a number or text, got {self.default!r}")
        if self.choices is not None:
            if not all(isinstance(choice, str) for choice in self.choices):
                raise ValueError(f"{self.key}: every choice must be text")
            if self.default not in self.choices:
                raise ValueError(f"{self.key}: the default {self.default!r} is not one of the choices")

    def validate(self, value: object) -> SettingValue:
        """Return ``value`` if this setting can hold it.

        Args:
            value: The value to check.

        Returns:
            The same value.

        Raises:
            InvalidValueError: If the value is the wrong kind, or a choice
                outside the list. A bool is never accepted for a whole-number
                or number setting, and a whole number is accepted for a
                number setting.
        """
        kind = type(self.default)
        if kind is float:
            ok = type(value) in (int, float)
        else:
            ok = type(value) is kind
        if ok and self.choices is not None:
            ok = value in self.choices
        if not ok:
            raise InvalidValueError(f"{self.key} cannot hold {value!r}")
        return value  # type: ignore[return-value]


def validate_definitions(definitions: Iterable[SettingDefinition]) -> tuple[SettingDefinition, ...]:
    """Return ``definitions`` as a tuple, after checking that no key repeats.

    Args:
        definitions: The declarations to check.

    Returns:
        The declarations, in the order given.

    Raises:
        ValueError: If two declarations share a key.
    """
    checked = tuple(definitions)
    seen: set[str] = set()
    for definition in checked:
        if definition.key in seen:
            raise ValueError(f"Setting {definition.key} is declared more than once")
        seen.add(definition.key)
    return checked


USER_SETTINGS = validate_definitions(
    [
        SettingDefinition(CONFIRM_CAMERA_DELETE, "Cameras", True),
        SettingDefinition(AUTO_OPEN_CAMERA_MONITOR, "Camera Monitor", False),
    ]
)
