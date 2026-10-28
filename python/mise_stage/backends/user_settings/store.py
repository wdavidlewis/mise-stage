"""Reading and writing an artist's user settings file.

The file is a flat YAML mapping of setting key to value. A read loads it every
time and takes no lock: every write builds a whole new file and swaps it in,
so a read sees the old file or the new one and never half of one.
"""
import logging
import os
import tempfile
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, NamedTuple, TypeVar

import yaml

from .definitions import USER_SETTINGS, SettingDefinition, SettingValue, validate_definitions
from .errors import InvalidValueError, SettingsWriteError, UnknownGroupError, UnknownSettingError
from .location import default_directory
from .lock import FileLock

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


class _FileContents(NamedTuple):
    """What was found in the settings file.

    Attributes:
        data: The file's mapping of keys to values; empty when the file is
            missing, empty or unreadable.
        problem: Why the file cannot be used, or None when it can. A missing
            or empty file has no problem.
    """

    data: dict[str, Any]
    problem: str | None


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

    def reset_group(self, group: str) -> None:
        """Return every setting in a group to its default.

        The group's keys are removed from the file, so the settings follow later
        changes to the defaults. Other groups, and keys no declaration names,
        are not touched. With no file, or none of the group's keys in it,
        nothing is written and no file is created.

        Args:
            group: The name of a declared group.

        Raises:
            UnknownGroupError: If no declaration is in this group.
            SettingsWriteError: If the file could not be written.
        """
        keys = [key for key, definition in self._definitions.items() if definition.group == group]
        if not keys:
            raise UnknownGroupError(f"No user settings group named {group!r}")
        self._reset(keys)

    def reset_all(self) -> None:
        """Return every user setting to its default.

        The file is kept, even when nothing is left in it.

        Raises:
            SettingsWriteError: If the file could not be written.
        """
        self._reset(list(self._definitions))

    def _reset(self, keys: list[str]) -> None:
        """Remove ``keys`` from the file, then drop any values held from failed saves for them.

        The held values are kept if the reset itself fails. With no settings file
        there is nothing to remove, so no folder, lock or file is created. When
        there is a file, which keys it holds is decided under the lock, so a key
        another session adds just before the reset is removed too.
        """
        if os.path.exists(self.path):

            def change(data: dict[str, Any]) -> bool:
                present = [key for key in keys if key in data]
                for key in present:
                    del data[key]
                return bool(present)

            self._update(change, rewrite_unreadable=False)
        for key in keys:
            _held.pop(self._state_key(key), None)

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

    def set(self, key: str, value: SettingValue) -> None:
        """Set a setting and save it to the file straight away.

        Only this key changes in the file; other keys, including ones no
        declaration names, are kept. With no file yet, setting the default
        creates nothing. A file that cannot be parsed is renamed aside with an
        ``.invalid`` suffix before the new file is written.

        Args:
            key: The key of a declared setting.
            value: The new value. It must be one the setting can hold.

        Raises:
            UnknownSettingError: If no declaration has this key.
            InvalidValueError: If the setting cannot hold the value. Nothing is
                written.
            SettingsWriteError: If the file could not be written. The value is
                still held for the rest of the session and is what reads return
                until this setting is next set or reset successfully.
        """
        definition = self._definition(key)
        definition.validate(value)
        state_key = self._state_key(key)
        if not self.path.exists() and value == definition.default:
            _held.pop(state_key, None)
            return

        def change(data: dict[str, Any]) -> bool:
            data[key] = value
            return True

        try:
            self._update(change, rewrite_unreadable=True)
        except SettingsWriteError:
            _held[state_key] = value
            raise
        _held.pop(state_key, None)

    def _read(self) -> _FileContents:
        """Read the settings file as it is now.

        Raises:
            OSError: If the file exists but cannot be opened, even after retries.
        """
        try:
            text = _retry_if_busy(lambda: self.path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return _FileContents({}, None)
        except UnicodeDecodeError as exc:
            return _FileContents({}, f"the settings file is not valid UTF-8 text ({exc})")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            return _FileContents({}, f"the settings file is not valid YAML ({exc})")
        if data is None:
            return _FileContents({}, None)
        if not isinstance(data, dict):
            return _FileContents({}, "the settings file must hold a mapping of keys to values")
        return _FileContents({str(key): value for key, value in data.items()}, None)

    def _load(self) -> dict[str, Any]:
        """Return the settings file's mapping, or an empty one if it is missing or unreadable.

        An unreadable file (it cannot be opened, is not valid YAML, or is not a
        mapping) warns once. Keys no declaration names also warn once each.
        """
        try:
            contents = self._read()
        except OSError as exc:
            self._warn("", f"cannot read the settings file ({exc}); using defaults")
            return {}
        if contents.problem is not None:
            self._warn("", f"{contents.problem}; using defaults")
            return {}
        for key in contents.data:
            if key not in self._definitions:
                self._warn(key, f"ignoring {key}, which is not a user setting")
        return contents.data

    def _update(self, change: Callable[[dict[str, Any]], bool], *, rewrite_unreadable: bool) -> None:
        """Change the settings file: load it, apply ``change``, and write it back.

        Args:
            change: Edits the loaded mapping in place and returns whether
                anything changed.
            rewrite_unreadable: Whether a file that cannot be parsed is renamed
                aside and replaced. When False such a file is left alone.

        Raises:
            SettingsWriteError: If the folder, the lock or the swap fails.
        """
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            with FileLock(self.path.with_name(FILE_NAME + ".lock")):
                contents = self._read()
                if contents.problem is not None and not rewrite_unreadable:
                    return
                data = contents.data
                if not change(data) and contents.problem is None:
                    return
                if contents.problem is not None:
                    invalid = self.path.with_name(FILE_NAME + ".invalid")
                    _retry_if_busy(lambda: os.replace(self.path, invalid))
                self._write(data)
        except OSError as exc:
            raise SettingsWriteError(f"Cannot write {self.path}: {exc}") from exc

    def _write(self, data: dict[str, Any]) -> None:
        """Write ``data`` as the whole settings file, swapping it in so a read never sees half of it.

        Raises:
            PermissionError: If the settings file exists and is read-only. The swap
                would replace it on POSIX, where only the folder's permissions count.
            OSError: If the temporary file cannot be written or swapped in.
        """
        if os.path.exists(self.path) and not os.access(self.path, os.W_OK):
            raise PermissionError(f"{self.path} is read-only")
        fd, tmp = tempfile.mkstemp(dir=self._directory, prefix=".user_settings-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            _retry_if_busy(lambda: os.replace(tmp, self.path))
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
