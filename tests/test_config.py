import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = REPO_ROOT / "python"

# The module loads on import, so a developer's own SHOW must not leak into it.
os.environ.pop("SHOW", None)
sys.path.insert(0, str(PYTHON_DIR))

from utils.config import ConfigError, _load_settings  # noqa: E402


def write_config_dir(tmp, defaults, shows=None):
    """Create a config dir with defaults.yaml and any {show: yaml_text} files."""
    config_dir = Path(tmp)
    (config_dir / "defaults.yaml").write_text(defaults)
    for show, text in (shows or {}).items():
        (config_dir / f"{show}.yaml").write_text(text)
    return config_dir


DEFAULTS = "DEFAULT_RENDER_WIDTH: 1920\nDEFAULT_RENDER_HEIGHT: 1080\n"


class LoadSettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def test_unset_show_returns_defaults(self):
        config_dir = write_config_dir(self.tmp, DEFAULTS)
        self.assertEqual(
            _load_settings(None, config_dir),
            {"DEFAULT_RENDER_WIDTH": 1920, "DEFAULT_RENDER_HEIGHT": 1080},
        )

    def test_empty_show_returns_defaults(self):
        config_dir = write_config_dir(self.tmp, DEFAULTS)
        self.assertEqual(_load_settings("", config_dir)["DEFAULT_RENDER_WIDTH"], 1920)

    def test_unset_show_logs_warning(self):
        config_dir = write_config_dir(self.tmp, DEFAULTS)
        with self.assertLogs("utils.config", level="WARNING"):
            _load_settings(None, config_dir)
        with self.assertLogs("utils.config", level="WARNING"):
            _load_settings("", config_dir)

    def test_show_overrides_only_listed_keys(self):
        config_dir = write_config_dir(
            self.tmp, DEFAULTS, {"abc": "DEFAULT_RENDER_WIDTH: 2048\n"}
        )
        settings = _load_settings("abc", config_dir)
        self.assertEqual(settings["DEFAULT_RENDER_WIDTH"], 2048)
        self.assertEqual(settings["DEFAULT_RENDER_HEIGHT"], 1080)
        self.assertIsInstance(settings["DEFAULT_RENDER_WIDTH"], int)

    def test_missing_show_file_names_show_and_path(self):
        config_dir = write_config_dir(self.tmp, DEFAULTS)
        with self.assertRaises(ConfigError) as ctx:
            _load_settings("abc", config_dir)
        self.assertIn("abc", str(ctx.exception))
        self.assertIn(str(config_dir / "abc.yaml"), str(ctx.exception))

    def test_unknown_key_names_key_and_file(self):
        config_dir = write_config_dir(
            self.tmp, DEFAULTS, {"abc": "NOT_A_SETTING: 1\n"}
        )
        with self.assertRaises(ConfigError) as ctx:
            _load_settings("abc", config_dir)
        self.assertIn("NOT_A_SETTING", str(ctx.exception))
        self.assertIn("abc.yaml", str(ctx.exception))

    def test_non_alphanumeric_show_rejected_before_any_read(self):
        missing_dir = Path(self.tmp) / "does-not-exist"
        for bad in ("../x", "a-b", "a b"):
            with self.subTest(show=bad):
                with self.assertRaises(ConfigError) as ctx:
                    _load_settings(bad, missing_dir)
                self.assertIn(bad, str(ctx.exception))

    def test_empty_show_file_means_no_overrides(self):
        config_dir = write_config_dir(self.tmp, DEFAULTS, {"abc": ""})
        self.assertEqual(
            _load_settings("abc", config_dir),
            {"DEFAULT_RENDER_WIDTH": 1920, "DEFAULT_RENDER_HEIGHT": 1080},
        )


class ImportTests(unittest.TestCase):
    def run_import(self, show):
        env = {k: v for k, v in os.environ.items() if k != "SHOW"}
        env["PYTHONPATH"] = str(PYTHON_DIR)
        if show is not None:
            env["SHOW"] = show
        code = "from utils import config; print(config.DEFAULT_RENDER_WIDTH, config.DEFAULT_RENDER_HEIGHT)"
        return subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True
        )

    def test_import_exposes_defaults_attributes(self):
        result = self.run_import(None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["1920", "1080"])

    def test_import_with_unknown_show_fails(self):
        result = self.run_import("nosuchshow")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ConfigError", result.stderr)
        self.assertIn("nosuchshow", result.stderr)


if __name__ == "__main__":
    unittest.main()
