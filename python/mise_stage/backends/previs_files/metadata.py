"""Comment metadata kept in a meta.json file inside an action or version folder.

The file is a JSON object; only the "comment" key is used today, and any other
keys are left alone so fields can be added later without a format change.
"""
import json
import os
import tempfile
import time
from pathlib import Path

from .errors import MetadataError

META_FILE_NAME = "meta.json"
_ATTEMPTS = 20
_PAUSE = 0.01


def _retry_if_busy(operation):
    """Run ``operation``, riding out Windows' brief sharing violations.

    Windows refuses to open or replace a file with PermissionError while another
    writer is replacing it; that clears within milliseconds, so retry a few
    times before giving up.
    """
    for attempt in range(_ATTEMPTS):
        try:
            return operation()
        except PermissionError:
            if attempt == _ATTEMPTS - 1:
                raise
            time.sleep(_PAUSE * (attempt + 1))


def _read_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def _load(path):
    try:
        data = _retry_if_busy(lambda: _read_json(path))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise MetadataError(f"Cannot read metadata file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MetadataError(f"Metadata file {path} must hold a JSON object")
    return data


def read_comment(folder):
    """Return the comment stored in ``folder``, or "" when there is none."""
    path = Path(folder) / META_FILE_NAME
    comment = _load(path).get("comment", "")
    if not isinstance(comment, str):
        raise MetadataError(f"The comment in {path} must be a string")
    return comment


def write_comment(folder, comment):
    """Store ``comment`` in ``folder``; a reader never sees a half-written file."""
    if not isinstance(comment, str):
        raise TypeError(f"comment must be a str, got {type(comment).__name__}")
    path = Path(folder) / META_FILE_NAME
    data = _load(path)
    data["comment"] = comment

    # A unique temporary name keeps two simultaneous writers apart.
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".meta-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _retry_if_busy(lambda: os.replace(tmp, path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
