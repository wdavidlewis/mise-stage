"""Comment metadata kept in a meta.json file inside an action or version folder.

The file is a JSON object; only the "comment" key is used today, and any other
keys are left alone so fields can be added later without a format change.
"""
import json
import os
import stat
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from .errors import MetadataError

META_FILE_NAME = "meta.json"
_ATTEMPTS = 20
_PAUSE = 0.01

_T = TypeVar("_T")


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


def _read_json(path: Path) -> Any:
    """Return the parsed JSON in ``path``, accepting a UTF-8 byte order mark."""
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _load(path: Path) -> dict[str, Any]:
    """Return the JSON object in ``path``, or an empty dict if the file is missing.

    Raises:
        MetadataError: If the file cannot be read or does not hold a JSON object.
    """
    try:
        data = _retry_if_busy(lambda: _read_json(path))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise MetadataError(f"Cannot read metadata file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MetadataError(f"Metadata file {path} must hold a JSON object")
    return data


def _shared_mode(path: Path, folder: Path) -> int:
    """Return the permission bits the replacement file should carry.

    mkstemp creates files readable and writable by their owner only, and
    os.replace would pass that on to meta.json, locking out other artists on a
    shared POSIX tree. An existing file keeps its own bits; a new one follows
    its folder's, without execute bits.
    """
    try:
        return stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        return stat.S_IMODE(os.stat(folder).st_mode) & 0o666


def read_comment(folder: str | os.PathLike[str]) -> str:
    """Return the comment stored in ``folder``, or "" when there is none.

    Raises:
        MetadataError: If the metadata file cannot be read or its comment is not
            a string.
    """
    path = Path(folder) / META_FILE_NAME
    comment = _load(path).get("comment", "")
    if not isinstance(comment, str):
        raise MetadataError(f"The comment in {path} must be a string")
    return comment


def write_comment(folder: str | os.PathLike[str], comment: str) -> None:
    """Store ``comment`` in ``folder``; a reader never sees a half-written file.

    Raises:
        TypeError: If ``comment`` is not a string.
        MetadataError: If the existing metadata file cannot be read.
    """
    if not isinstance(comment, str):
        raise TypeError(f"comment must be a str, got {type(comment).__name__}")
    folder = Path(folder)
    path = folder / META_FILE_NAME
    data = _load(path)
    data["comment"] = comment

    # A unique temporary name keeps two simultaneous writers apart.
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".meta-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(tmp, _shared_mode(path, folder))
        except OSError:
            pass  # a filesystem without permission bits; the save still works
        _retry_if_busy(lambda: os.replace(tmp, path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
