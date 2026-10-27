"""Tests for the workspace callback script and the Maya-free import of the dcc layer."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = REPO_ROOT / "python"
sys.path.insert(0, str(PYTHON_DIR))

from mise_stage.dcc.workspace import callback_script  # noqa: E402

CALLBACK_PATH = "fake_monitor_pkg.visible_changed"


class CallbackScriptTests(unittest.TestCase):
    """Run the generated script the way Maya does for a workspace panel callback."""

    def setUp(self) -> None:
        self._saved = sys.modules.pop("fake_monitor_pkg", None)
        self._path = list(sys.path)

    def tearDown(self) -> None:
        sys.modules.pop("fake_monitor_pkg", None)
        if self._saved is not None:
            sys.modules["fake_monitor_pkg"] = self._saved
        sys.path[:] = self._path

    def run_script(self) -> None:
        exec(compile(callback_script(CALLBACK_PATH), "<callback>", "exec"), {})

    def write_package(self, source: str) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / "fake_monitor_pkg.py").write_text(source)
        sys.path.insert(0, tmp.name)

    def test_missing_package_is_silent_and_does_not_raise(self) -> None:
        self.run_script()

        self.assertNotIn("fake_monitor_pkg", sys.modules)

    def test_present_package_has_function_called_exactly_once(self) -> None:
        self.write_package("calls = []\ndef visible_changed():\n    calls.append(1)\n")

        self.run_script()

        self.assertEqual(sys.modules["fake_monitor_pkg"].calls, [1])

    def test_error_raised_by_the_function_propagates(self) -> None:
        self.write_package("def visible_changed():\n    raise RuntimeError('monitor bug')\n")

        with self.assertRaisesRegex(RuntimeError, "monitor bug"):
            self.run_script()

    def test_script_compiles_and_names_the_function(self) -> None:
        script = callback_script("mise_stage.ui.camera_monitor.controller.visible_changed")

        compile(script, "<callback>", "exec")
        self.assertIn("mise_stage.ui.camera_monitor.controller", script)
        self.assertIn("visible_changed", script)


class ImportHygieneTests(unittest.TestCase):
    def test_dcc_modules_import_without_maya_or_qt(self) -> None:
        self.assertNotIn("maya", sys.modules)
        import mise_stage.dcc.camera_monitor  # noqa: F401
        import mise_stage.dcc.workspace  # noqa: F401

        self.assertNotIn("maya", sys.modules)
        self.assertNotIn("PySide6", sys.modules)


if __name__ == "__main__":
    unittest.main()
