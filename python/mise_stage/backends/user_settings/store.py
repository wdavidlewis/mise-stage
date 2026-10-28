"""Reading and writing an artist's user settings file.

The file is a flat YAML mapping of setting key to value. A read loads it every
time and takes no lock: every write builds a whole new file and swaps it in,
so a read sees the old file or the new one and never half of one.
"""
import logging
import os
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, TypeVar

import yaml

from .definitions import USER_SETTINGS, SettingDefinition, SettingValue, validate_definitions
from .errors import InvalidValueError, UnknownSettingError
from .location import default_directory

log = logging.getLogger(__name__)

FILE_NAME = "user_settings.yaml"
_ATTEMPTS = 20
_PAUSE = 0.01

_T = TypeVar("_T")

# Session state is per process, because "once per Maya session" and "for the
# rest of the session" both mean the process, and features may each build their
# own store object. Keys are (settings file path, setting key); the key is ""
# for a warning about the file itself.
_warned: set[tuple[str, str]] = set()
_held: dict[tuple[str, str], SettingValue] = {}


def _reset_session_state() -> None:
    """Forget the warnings given and the values held from failed saves; for tests."""
    _warned.clear()
    _held.clear()


def _retry_if_busy(operation: Callable[[], _T]) -> _T:
    """Run ``operation``, riding out Windows' brief sharing violations.

    Windows refuses to open or replace a file with PermissionError while another
    writer is replacing it; that clears within milliseconds, so retry a few
    times before giving up.

    Args:
        operation: The file operation to run. It is called again on each retry.

    Returns:
        The value returned by ``operation``.

    Raises:
        PermissionError: If the file is still busy after the last attempt.
    """
    for attempt in range(_ATTEMPTS):
        try:
            return operation()
        except PermissionError:
            if attempt == _ATTEMPTS - 1:
                raise
            time.sleep(_PAUSE * (attempt + 1))
    raise AssertionError("unreachable")


class UserSettings:
    """One artist's user settings, read from and written to a settings file.

    Args:
        directory: The folder holding the settings file. None means the
            operating system's per-user app-data folder.
        definitions: The declared settings. Defaults to the shipped ones.

    Raises:
        ValueError: If two declarations share a key.
    """

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        definitions: Iterable[SettingDefinition] = USER_SETTINGS,
    ) -> None:
        self._directory = Path(directory) if directory is not None else default_directory()
        self._definitions = {d.key: d for d in validate_definitions(definitions)}

    @property
    def path(self) -> Path:
        """The settings file. It may not exist yet."""
        return self._directory / FILE_NAME

    def get(self, key: str) -> SettingValue:
        """Return the current value of a setting.

        Args:
            key: The key of a declared setting.

        Returns:
            The value held from a failed save if there is one, else the value in
            the file as it is now, else the setting's default. A value in the
            file that the setting cannot hold reads as the default, with one
            warning per session.

        Raises:
            UnknownSettingError: If no declaration has this key.
        """
        definition = self._definition(key)
        held = _held.get(self._state_key(key))
        if held is not None:
            return held
        data = self._load()
        if key not in data:
            return definition.default
        try:
            return definition.validate(data[key])
        except InvalidValueError as exc:
            self._warn(key, f"{exc}; using the default {definition.default!r}")
            return definition.default

    def _definition(self, key: str) -> SettingDefinition:
        """Return the declaration for ``key``, or raise UnknownSettingError."""
        try:
            return self._definitions[key]
        except KeyError:
            raise UnknownSettingError(f"No user setting named {key!r}") from None

    def _state_key(self, key: str) -> tuple[str, str]:
        """Return the key under which session state is kept for ``key``."""
        return (os.path.abspath(self.path), key)

    def _warn(self, key: str, message: str) -> None:
        """Log ``message`` once per session for this file and key."""
        state_key = self._state_key(key)
        if state_key in _warned:
            return
        _warned.add(state_key)
        log.warning("%s: %s", self.path, message)

    def _load(self) -> dict[str, Any]:
        """Return the settings file's mapping, or an empty one if it is missing or unreadable.

        An unreadable file (it cannot be opened, is not valid YAML, or is not a
        mapping) warns once. Keys no declaration names also warn once each.
        """
        try:
            text = _retry_if_busy(lambda: self.path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return {}
        except OSError as exc:
            self._warn("", f"cannot read the settings file ({exc}); using defaults")
            return {}
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            self._warn("", f"the settings file is not valid YAML ({exc}); using defaults")
            return {}
        if data is None:
            return {}
        if not isinstance(data, dict):
            self._warn("", "the settings file must hold a mapping of keys to values; using defaults")
            return {}
        data = {str(key): value for key, value in data.items()}
        for key in data:
            if key not in self._definitions:
                self._warn(key, f"ignoring {key}, which is not a user setting")
        return data
