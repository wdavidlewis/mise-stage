"""User settings: artist-local values kept in a file in the artist's profile folder."""
from . import lock, store
from .definitions import (
    AUTO_OPEN_CAMERA_MONITOR,
    CONFIRM_CAMERA_DELETE,
    USER_SETTINGS,
    SettingDefinition,
    SettingValue,
    validate_definitions,
)
from .errors import (
    InvalidValueError,
    SettingsWriteError,
    UnknownGroupError,
    UnknownSettingError,
    UserSettingsError,
)
from .location import default_directory
from .store import UserSettings

__all__ = [
    "AUTO_OPEN_CAMERA_MONITOR",
    "CONFIRM_CAMERA_DELETE",
    "InvalidValueError",
    "SettingDefinition",
    "SettingValue",
    "SettingsWriteError",
    "USER_SETTINGS",
    "UnknownGroupError",
    "UnknownSettingError",
    "UserSettings",
    "UserSettingsError",
    "default_directory",
    "lock",
    "store",
    "validate_definitions",
]
