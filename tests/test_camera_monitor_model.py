import ast
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))

from mise_stage.ui.camera_monitor import model  # noqa: E402
from mise_stage.ui.shell import model as shell_model  # noqa: E402


class ModelTests(unittest.TestCase):
    def test_names_differ_from_the_shells_so_the_two_panels_never_collide(self):
        self.assertNotEqual(model.CONTROL_NAME, shell_model.CONTROL_NAME)
        self.assertNotEqual(model.PANEL_NAME, shell_model.CONTROL_NAME)
        self.assertNotEqual(model.PANEL_NAME, model.CONTROL_NAME)

    def test_rebuild_path_names_the_controller_not_the_lazy_package_function(self):
        # Loading the controller (and so Qt) must happen inside the restore script's guard.
        self.assertEqual(model.REBUILD_PATH, "mise_stage.ui.camera_monitor.controller.rebuild")

    def test_callback_paths_name_controller_functions(self):
        self.assertEqual(model.VISIBLE_CHANGE_PATH, "mise_stage.ui.camera_monitor.controller.visible_changed")
        self.assertEqual(model.SAVE_STATE_PATH, "mise_stage.ui.camera_monitor.controller.save_state")

    def test_callback_paths_name_functions_that_exist_in_the_controller(self):
        # Maya calls these by name, so a rename would pass CI and only fail inside Maya.
        controller = REPO_ROOT / "python" / "mise_stage" / "ui" / "camera_monitor" / "controller.py"
        defined = {node.name for node in ast.parse(controller.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef)}

        for path in (model.REBUILD_PATH, model.VISIBLE_CHANGE_PATH, model.SAVE_STATE_PATH):
            module, _, function = path.rpartition(".")
            self.assertEqual(module, "mise_stage.ui.camera_monitor.controller")
            self.assertIn(function, defined, path)

    def test_monitor_looks_through_persp(self):
        self.assertEqual(model.CAMERA, "persp")


class ImportHygieneTests(unittest.TestCase):
    def test_package_and_model_import_without_maya_or_qt(self):
        # Run in a fresh interpreter: other test modules may have loaded Qt or Maya stubs.
        import subprocess

        code = (
            "import sys; sys.path.insert(0, %r)\n"
            "import mise_stage.ui.camera_monitor, mise_stage.ui.camera_monitor.model\n"
            "bad = [m for m in ('maya', 'PySide6', 'shiboken6') if m in sys.modules]\n"
            "sys.exit(1 if bad else 0)\n"
        ) % str(REPO_ROOT / "python")
        result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
