---
title: Smoke-test Maya Qt code headlessly with mayapy
date: 2026-10-25
category: developer-experience
module: ui/shell
problem_type: developer_experience
component: testing_framework
severity: medium
applies_when:
  - Building or changing a Qt view or controller under python/mise_stage/ui/
  - Checking a Maya restore script without opening the Maya GUI
tags: [maya, pyside6, mayapy, qt, offscreen, testing]
---

# Smoke-test Maya Qt code headlessly with mayapy

## Context

CI has neither Maya nor PySide6, so `python/mise_stage/ui/` code has no automated tests, and checking it in the Maya GUI is slow. While building the shell panel (#15, PR #17), a headless run with Maya's own Python found a real bug before the hand checks, and exposed two gotchas that look like failures of the code under test.

## Guidance

Maya 2026's `mayapy.exe` ships PySide6 6.5.3. Run a short script with it, using the offscreen Qt platform and `-I`:

```bash
QT_QPA_PLATFORM=offscreen "C:/Program Files/Autodesk/Maya2026/bin/mayapy.exe" -I smoke.py
```

`-I` ignores `PYTHONPATH` and the current directory, so the script adds the repo's `python/` folder to `sys.path` itself. Create a `QApplication`, then build the view or controller and exercise it.

To test controller logic that normally talks to Maya, patch the `dcc/workspace` functions the controller calls. For the panel container, use a plain `QWidget` and return its address from `shiboken6.getCppPointer`. That is enough to check that `rebuild()` is idempotent and recovers after the shell widget is deleted, the way Maya deletes it.

Two gotchas:

- **PySide6 6.5 frees a menu made by `menuBar().addMenu("File")`.** Once the Python wrapper goes out of scope the C++ menu is deleted, and later use raises `RuntimeError: Internal C++ object (QMenu) already deleted`. Create the menu with an explicit parent instead: `QMenu("&File", self)`, then `menuBar().addMenu(menu)` (`python/mise_stage/ui/shell/view.py`).
- **`maya.cmds.warning` does not exist until `maya.standalone.initialize()` has run.** Without it, a check of a restore script's warning branch fails with `AttributeError` and looks like a bug in the script.

## Why This Matters

The `QMenu` bug showed no symptom in the code review or the unit tests and would only have surfaced in the Maya GUI. The `maya.cmds` gotcha sends you looking for a fault in code that is fine.

## When to Apply

- Any new view, controller or restore-script change under `python/mise_stage/ui/` or `python/mise_stage/dcc/` that CI cannot import.
- Not a substitute for the Maya GUI: docking, floating and workspace-panel restore still need a hand check (see `docs/technical/shell.md`).

## Examples

- Build `ShellView`, trigger File ▸ Exit, and assert `exit_requested` fired.
- Call `controller.rebuild()` twice and assert one shell child. Delete the shell, call `rebuild()` again, and assert there is one again.
- Run `restore_script(...)` with `sys.modules['PySide6'] = None` to confirm a Qt import failure produces the single warning and no traceback.
