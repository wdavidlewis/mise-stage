"""Per-show settings.

Settings load once, on first import, from config/defaults.yaml overlaid by
config/<SHOW>.yaml when the SHOW environment variable is set. Each key becomes
an attribute of this module, e.g. config.DEFAULT_RENDER_WIDTH.
"""
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

# Repo root is three directories above this package directory (python/mise_stage/config).
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


class ConfigError(Exception):
    """The show or its config files are invalid."""


def _read_yaml(path: Path) -> dict[str, Any]:
    """Return the YAML mapping in ``path``, or an empty dict if the file is empty."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_settings(show: str | None, config_dir: Path) -> dict[str, Any]:
    """Return the defaults overlaid with the overrides for ``show``.

    Args:
        show: The show code from the SHOW environment variable, or None or ""
            to load the defaults only.
        config_dir: The folder holding ``defaults.yaml`` and the show files.

    Returns:
        The merged settings, keyed by setting name.

    Raises:
        ConfigError: If the show code is not alphanumeric, its config file is
            missing, or it sets a key that ``defaults.yaml`` does not define.
    """
    if show and not re.fullmatch(r"[A-Za-z0-9]+", show):
        raise ConfigError(f"SHOW must be alphanumeric, got {show!r}")

    settings = _read_yaml(Path(config_dir) / "defaults.yaml")
    if not show:
        log.warning("SHOW is not set; using default settings only")
        return settings

    show_path = Path(config_dir) / f"{show}.yaml"
    if not show_path.is_file():
        raise ConfigError(f"No config for show {show!r}: expected {show_path}")

    overrides = _read_yaml(show_path)
    unknown = sorted(set(overrides) - set(settings))
    if unknown:
        raise ConfigError(
            f"{show_path} sets unknown keys not in defaults.yaml: {', '.join(unknown)}"
        )
    settings.update(overrides)
    return settings


globals().update(_load_settings(os.environ.get("SHOW"), CONFIG_DIR))
