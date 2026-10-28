"""A lock file that keeps two sessions from changing the settings file at once.

Creating the lock file with exclusive creation is the lock: only one session
can create it, and it works the same on Windows and POSIX. A lock file older
than ``STALE_AFTER`` seconds is taken to be left behind by a crashed session.
"""
import logging
import os
import time
from pathlib import Path
from types import TracebackType

from .errors import SettingsWriteError

log = logging.getLogger(__name__)

LOCK_WAIT = 5.0
STALE_AFTER = 30.0
_PAUSE = 0.01
_RELEASE_ATTEMPTS = 20


class FileLock:
    """Holds a lock file for the length of a ``with`` block.

    Args:
        path: The lock file to create. Its folder must exist.

    Raises:
        SettingsWriteError: From ``with``, if the lock could not be taken
            within ``LOCK_WAIT`` seconds.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)

    def __enter__(self) -> "FileLock":
        deadline = time.monotonic() + LOCK_WAIT
        while True:
            try:
                os.close(os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except (FileExistsError, PermissionError):
                # Another session holds it, or Windows is mid-delete of the file.
                pass
            if self._is_stale():
                self._remove()
                continue
            if time.monotonic() >= deadline:
                raise SettingsWriteError(f"Cannot get the lock {self._path}: another session is changing the settings")
            time.sleep(_PAUSE)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for attempt in range(_RELEASE_ATTEMPTS):
            try:
                os.unlink(self._path)
                return
            except FileNotFoundError:
                return
            except PermissionError:
                time.sleep(_PAUSE * (attempt + 1))
        log.warning("%s: could not remove the lock file; it is cleared once it is %s seconds old", self._path, STALE_AFTER)

    def _is_stale(self) -> bool:
        """Return whether the lock file is old enough to be from a crashed session."""
        try:
            return time.time() - os.stat(self._path).st_mtime > STALE_AFTER
        except OSError:
            return False

    def _remove(self) -> None:
        """Remove a stale lock file, ignoring a file that is already gone or busy."""
        try:
            os.unlink(self._path)
        except OSError:
            pass
