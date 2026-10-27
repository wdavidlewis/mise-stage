"""Names and numbers for the previs file tree.

Folders are <sequence>/a<action>/v<version> with zero-padded numbers, and a
scene file is <showcode>_<sequence>_a<action>_v<version>.<ext>. Sequences and
actions start at 0; versions start at 1. Widths are fixed, so a number past its
maximum is an error rather than a wider field.
"""
import re
from typing import Any, NamedTuple

from .errors import InvalidNameError, NumberOutOfRangeError

SEQUENCE_MIN, SEQUENCE_MAX = 0, 9999
ACTION_MIN, ACTION_MAX = 0, 999
VERSION_MIN, VERSION_MAX = 1, 999

# [0-9], not \d, so that other scripts' digits never match.
_SHOW_RE = re.compile(r"[A-Za-z0-9]+")
_EXTENSION_RE = re.compile(r"\.?([A-Za-z0-9]+)")
_SEQUENCE_DIR_RE = re.compile(r"([0-9]{4})")
_ACTION_DIR_RE = re.compile(r"a([0-9]{3})")
_VERSION_DIR_RE = re.compile(r"v([0-9]{3})")
_SCENE_NAME_RE = re.compile(
    r"([A-Za-z0-9]+)_([0-9]{4})_a([0-9]{3})_v([0-9]{3})"
)


class SceneName(NamedTuple):
    """The parts of a scene name.

    Attributes:
        show: The show code.
        sequence: The sequence number.
        action: The action number.
        version: The version number.
    """

    show: str
    sequence: int
    action: int
    version: int


def _check(kind: str, number: Any, low: int, high: int) -> int:
    """Return ``number`` if it is an int within ``low``..``high``.

    Raises:
        NumberOutOfRangeError: If ``number`` is not an int (a bool is rejected)
            or is outside the range.
    """
    if not isinstance(number, int) or isinstance(number, bool):
        raise NumberOutOfRangeError(f"{kind} number must be an integer, got {number!r}")
    if not low <= number <= high:
        raise NumberOutOfRangeError(
            f"{kind} number {number} is outside {low}..{high}"
        )
    return number


def check_sequence(number: Any) -> int:
    """Return ``number`` if it is a valid sequence number.

    Raises:
        NumberOutOfRangeError: If it is not a valid sequence number.
    """
    return _check("Sequence", number, SEQUENCE_MIN, SEQUENCE_MAX)


def check_action(number: Any) -> int:
    """Return ``number`` if it is a valid action number.

    Raises:
        NumberOutOfRangeError: If it is not a valid action number.
    """
    return _check("Action", number, ACTION_MIN, ACTION_MAX)


def check_version(number: Any) -> int:
    """Return ``number`` if it is a valid version number.

    Raises:
        NumberOutOfRangeError: If it is not a valid version number.
    """
    return _check("Version", number, VERSION_MIN, VERSION_MAX)


def check_show(show: Any) -> str:
    """Return ``show`` if it is a valid show code.

    Raises:
        InvalidNameError: If ``show`` is not a non-empty string of letters and digits.
    """
    if not isinstance(show, str) or not _SHOW_RE.fullmatch(show):
        raise InvalidNameError(f"Show code must be alphanumeric, got {show!r}")
    return show


def check_extension(ext: Any) -> str:
    """Return ``ext`` without its leading dot; it must be a plain alphanumeric extension.

    Raises:
        InvalidNameError: If ``ext`` is not letters and digits, with an optional
            leading dot.
    """
    match = _EXTENSION_RE.fullmatch(ext) if isinstance(ext, str) else None
    if not match:
        raise InvalidNameError(
            f"Extension must be letters and digits, like 'ma' or '.mb', got {ext!r}"
        )
    return match.group(1)


def sequence_dir_name(sequence: int) -> str:
    """Return the folder name for a sequence, such as ``"0100"``."""
    return f"{check_sequence(sequence):04d}"


def action_dir_name(action: int) -> str:
    """Return the folder name for an action, such as ``"a007"``."""
    return f"a{check_action(action):03d}"


def version_dir_name(version: int) -> str:
    """Return the folder name for a version, such as ``"v003"``."""
    return f"v{check_version(version):03d}"


def _parse_dir(pattern: re.Pattern[str], name: str, low: int, high: int) -> int | None:
    """Return the number in a folder name, or None if it does not match or is out of range."""
    match = pattern.fullmatch(name)
    if not match:
        return None
    number = int(match.group(1))
    return number if low <= number <= high else None


def parse_sequence_dir(name: str) -> int | None:
    """Return the sequence number for a folder name, or None if it doesn't match."""
    return _parse_dir(_SEQUENCE_DIR_RE, name, SEQUENCE_MIN, SEQUENCE_MAX)


def parse_action_dir(name: str) -> int | None:
    """Return the action number for a folder name, or None if it doesn't match."""
    return _parse_dir(_ACTION_DIR_RE, name, ACTION_MIN, ACTION_MAX)


def parse_version_dir(name: str) -> int | None:
    """Return the version number for a folder name, or None if it doesn't match."""
    return _parse_dir(_VERSION_DIR_RE, name, VERSION_MIN, VERSION_MAX)


def scene_name(show: str, sequence: int, action: int, version: int) -> str:
    """Build the scene name, without an extension.

    Raises:
        InvalidNameError: If ``show`` is not a valid show code.
        NumberOutOfRangeError: If a number is out of range.
    """
    check_show(show)
    return (
        f"{show}_{sequence_dir_name(sequence)}_{action_dir_name(action)}"
        f"_{version_dir_name(version)}"
    )


def parse_scene_name(name: str) -> SceneName:
    """Split a bare scene name (no extension) into its parts.

    Raises:
        InvalidNameError: If ``name`` does not follow the scene name convention.
        NumberOutOfRangeError: If the version number is out of range.
    """
    match = _SCENE_NAME_RE.fullmatch(name) if isinstance(name, str) else None
    if not match:
        raise InvalidNameError(
            f"Not a scene name <show>_<0000>_a<000>_v<000>: {name!r}"
        )
    show, sequence, action, version = match.groups()
    parts = SceneName(show, int(sequence), int(action), int(version))
    check_version(parts.version)
    return parts
