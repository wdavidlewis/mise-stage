"""Where an artist's user settings file lives."""
import os
import sys
from pathlib import Path

FOLDER_NAME = "mise-stage"


def default_directory() -> Path:
    """Return the folder that holds the user settings file.

    It is the operating system's per-user app-data folder, not Maya's
    preferences folder, so a Maya upgrade does not lose the settings:
    ``%APPDATA%`` on Windows, ``~/Library/Application Support`` on macOS, and
    ``$XDG_CONFIG_HOME`` or ``~/.config`` elsewhere.

    Returns:
        The ``mise-stage`` folder inside that location. It may not exist yet.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / FOLDER_NAME
