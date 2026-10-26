"""Names and numbers for the previs file tree.

Folders are <sequence>/a<action>/v<version> with zero-padded numbers, and a
scene file is <showcode>_<sequence>_a<action>_v<version>.<ext>. Sequences and
actions start at 0; versions start at 1. Widths are fixed, so a number past its
maximum is an error rather than a wider field.
"""
import re
from typing import NamedTuple

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
    show: str
    sequence: int
    action: int
    version: int


def _check(kind, number, low, high):
    if not isinstance(number, int) or isinstance(number, bool):
        raise NumberOutOfRangeError(f"{kind} number must be an integer, got {number!r}")
    if not low <= number <= high:
        raise NumberOutOfRangeError(
            f"{kind} number {number} is outside {low}..{high}"
        )
    return number


def check_sequence(number):
    return _check("Sequence", number, SEQUENCE_MIN, SEQUENCE_MAX)


def check_action(number):
    return _check("Action", number, ACTION_MIN, ACTION_MAX)


def check_version(number):
    return _check("Version", number, VERSION_MIN, VERSION_MAX)


def check_show(show):
    if not isinstance(show, str) or not _SHOW_RE.fullmatch(show):
        raise InvalidNameError(f"Show code must be alphanumeric, got {show!r}")
    return show


def check_extension(ext):
    """Return ``ext`` without its leading dot; it must be a plain alphanumeric extension."""
    match = _EXTENSION_RE.fullmatch(ext) if isinstance(ext, str) else None
    if not match:
        raise InvalidNameError(
            f"Extension must be letters and digits, like 'ma' or '.mb', got {ext!r}"
        )
    return match.group(1)


def sequence_dir_name(sequence):
    return f"{check_sequence(sequence):04d}"


def action_dir_name(action):
    return f"a{check_action(action):03d}"


def version_dir_name(version):
    return f"v{check_version(version):03d}"


def _parse_dir(pattern, name, low, high):
    match = pattern.fullmatch(name)
    if not match:
        return None
    number = int(match.group(1))
    return number if low <= number <= high else None


def parse_sequence_dir(name):
    """Return the sequence number for a folder name, or None if it doesn't match."""
    return _parse_dir(_SEQUENCE_DIR_RE, name, SEQUENCE_MIN, SEQUENCE_MAX)


def parse_action_dir(name):
    """Return the action number for a folder name, or None if it doesn't match."""
    return _parse_dir(_ACTION_DIR_RE, name, ACTION_MIN, ACTION_MAX)


def parse_version_dir(name):
    """Return the version number for a folder name, or None if it doesn't match."""
    return _parse_dir(_VERSION_DIR_RE, name, VERSION_MIN, VERSION_MAX)


def scene_name(show, sequence, action, version):
    """Build the scene name, without an extension."""
    check_show(show)
    return (
        f"{show}_{sequence_dir_name(sequence)}_{action_dir_name(action)}"
        f"_{version_dir_name(version)}"
    )


def parse_scene_name(name):
    """Split a bare scene name (no extension) into its parts."""
    match = _SCENE_NAME_RE.fullmatch(name) if isinstance(name, str) else None
    if not match:
        raise InvalidNameError(
            f"Not a scene name <show>_<0000>_a<000>_v<000>: {name!r}"
        )
    show, sequence, action, version = match.groups()
    parts = SceneName(show, int(sequence), int(action), int(version))
    check_version(parts.version)
    return parts
