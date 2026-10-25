"""Per-show settings.

Settings load once, on first import, from config/defaults.yaml overlaid by
config/<SHOW>.yaml when the SHOW environment variable is set. Each key becomes
an attribute of this module, e.g. config.DEFAULT_RENDER_WIDTH.
"""
import logging
import os
import re
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

# Repo root is three directories above this package directory (python/mise_stage/config).
CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


class ConfigError(Exception):
    """The show or its config files are invalid."""


def _read_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_settings(show, config_dir):
    """Return the defaults overlaid with the overrides for ``show``."""
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
