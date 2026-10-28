"""Errors raised by the user settings API."""


class UserSettingsError(Exception):
    """Base class: anything wrong with a user setting or a request on it."""


class UnknownSettingError(UserSettingsError):
    """A setting that no declaration names was read or set."""


class UnknownGroupError(UserSettingsError):
    """A group that no declaration names was reset."""


class InvalidValueError(UserSettingsError):
    """A value the setting cannot hold: the wrong kind, or a choice outside its list."""


class SettingsWriteError(UserSettingsError):
    """The settings file could not be written, or its lock could not be taken."""
