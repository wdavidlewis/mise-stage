import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = REPO_ROOT / "python"
sys.path.insert(0, str(PYTHON_DIR))

from mise_stage.dcc.workspace import restore_script  # noqa: E402

REBUILD_PATH = "fake_shell_pkg.rebuild"


class RestoreScriptTests(unittest.TestCase):
    """Run the generated script the way Maya does: exec'd with only `maya.cmds` around."""

    def setUp(self):
        self.warnings = []
        maya = types.ModuleType("maya")
        cmds = types.ModuleType("maya.cmds")
        cmds.warning = self.warnings.append
        maya.cmds = cmds
        self._saved = {k: sys.modules.get(k) for k in ("maya", "maya.cmds", "fake_shell_pkg")}
        sys.modules["maya"] = maya
        sys.modules["maya.cmds"] = cmds
        sys.modules.pop("fake_shell_pkg", None)
        self._path = list(sys.path)

    def tearDown(self):
        for name, mod in self._saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod
        sys.path[:] = self._path

    def run_script(self):
        exec(compile(restore_script(REBUILD_PATH), "<restore>", "exec"), {})

    def write_package(self, source):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / "fake_shell_pkg.py").write_text(source)
        sys.path.insert(0, tmp.name)

    def test_missing_package_warns_once_and_does_not_raise(self):
        self.run_script()

        self.assertEqual(len(self.warnings), 1)
        self.assertIn("fake_shell_pkg", self.warnings[0])
        self.assertIn("sys.path", self.warnings[0])

    def test_import_error_inside_the_package_is_warned_not_raised(self):
        self.write_package("import a_dependency_that_does_not_exist_xyz\n")

        self.run_script()

        self.assertEqual(len(self.warnings), 1)
        self.assertIn("a_dependency_that_does_not_exist_xyz", self.warnings[0])

    def test_present_package_has_rebuild_called_exactly_once(self):
        self.write_package("calls = []\ndef rebuild():\n    calls.append(1)\n")

        self.run_script()

        self.assertEqual(sys.modules["fake_shell_pkg"].calls, [1])
        self.assertEqual(self.warnings, [])

    def test_error_raised_by_rebuild_propagates(self):
        self.write_package("def rebuild():\n    raise RuntimeError('shell bug')\n")

        with self.assertRaisesRegex(RuntimeError, "shell bug"):
            self.run_script()

        self.assertEqual(self.warnings, [])

    def test_script_compiles_and_names_the_rebuild_function(self):
        script = restore_script("mise_stage.ui.shell.rebuild")

        compile(script, "<restore>", "exec")
        self.assertIn("mise_stage.ui.shell", script)
        self.assertIn("rebuild", script)


class ImportHygieneTests(unittest.TestCase):
    def test_workspace_module_imports_without_maya(self):
        self.assertNotIn("maya", sys.modules)
        import mise_stage.dcc.workspace  # noqa: F401

        self.assertNotIn("maya", sys.modules)


if __name__ == "__main__":
    unittest.main()
