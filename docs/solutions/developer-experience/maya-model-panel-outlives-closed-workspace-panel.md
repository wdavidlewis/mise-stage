---
title: A Maya model panel outlives its closed workspace panel
date: 2026-10-26
category: developer-experience
module: ui/camera_monitor
problem_type: developer_experience
component: frontend
severity: high
applies_when:
  - Putting a Maya model panel (or any panel built with cmds) inside a workspaceControl created with retain=False
  - Writing the restore or rebuild function Maya re-runs for a workspace panel
  - Saving a panel's state when it hides or when Maya quits
symptoms:
  - Reopening the panel shows an empty grey tab with no 3D view
  - The panel's layout appears inside the Script Editor window instead of the panel
  - Maya crashes while quitting after the panel was closed
  - "`NameError: name 'python' is not defined` from a callback string written in MEL style"
root_cause: wrong_api
resolution_type: code_fix
retire_when: Autodesk documents or changes how a closed workspaceControl treats the model panel inside it, observed on Maya 2026. Recheck by closing a retain=False workspaceControl in a new Maya release and querying the model panel with panel -query -control.
tags: [maya, workspacecontrol, modelpanel, lifecycle, restore-script, scriptjob, deleteui]
---

# A Maya model panel outlives its closed workspace panel

## Context

The camera monitor (#22) is a model panel inside a workspace panel created with `retain=False` and a restore script that Maya re-runs to fill it (`python/mise_stage/dcc/workspace.py:66-76`). Four failures and one surprising default looked like bugs in our code, and each came from how Maya manages the two objects. CI has no Maya, so none of them show up in the unit tests. They were found by running the panel in Maya 2026 and by one crash on quit.

## Guidance

**Closing the workspace panel does not close the model panel.** The control is destroyed (`workspaceControl -query -exists` is false), but the model panel stays in Maya with no parent: `modelPanel -query -exists` is still true and `panel -query -control` returns an empty string. So "the panel exists" does not mean "this workspace panel holds it". Count a panel as built only when its control path starts with the workspace panel's name and a pipe, and rebuild otherwise (`panel_in_control`, `python/mise_stage/dcc/camera_monitor.py:17-27`, used at `python/mise_stage/ui/camera_monitor/controller.py:37`). Checking only that the panel exists made the next open skip the build and show an empty grey tab.

**Never read a leftover panel.** The quit-time save asked the leftover panel for its editor state, and Maya crashed on quit when the monitor had been closed. It quit cleanly after the save was restricted to a panel inside the control (`controller.py:68-75`). The minidump held no readable frames, so the exact mechanism is not proven; the evidence is one crash with the monitor closed and clean quits after the guard.

**`deleteUI` changes the parent Maya builds into.** Deleting a stale panel and then calling `cmds.paneLayout(...)` built the new layout into the Script Editor window, next to its own layout. Create the layout first, delete the stale panel, then make the layout current again with `cmds.setParent(layout)` (`camera_monitor.py:42-45`).

**A new model panel opens in wireframe.** Set the look you want after creating it (`camera_monitor.py:50`).

**Callback strings are Python source, not MEL.** `visibleChangeCommand='python("...")'` raised `NameError: name 'python' is not defined`. Pass plain Python (`callback_script`, `workspace.py:33`). In a Maya 2026 probe the visible-change callback fired when the panel was docked, floated and closed, and when Maya quit, and the editor state was still readable at that moment. A `closeCommand` set the same way never fired. Closing a `retain=False` panel from a script also destroys it, so "is it open" can be "does the control exist".

## Why This Matters

Most of these were silent or fatal: a grey tab, a panel built into the wrong window, a crash on quit. None raise a Python error you would find in a test, and the quit crash loses the artist's open scene. The leftover model panel, the `deleteUI` parent reset and the visible-change versus close callback behavior are not in Autodesk's command reference.

## When to Apply

- Any new workspace panel that holds a `cmds`-built panel such as a model panel, outliner or script editor panel.
- Any restore or rebuild function Maya re-runs, because it can run when the control is new and when it is restored.
- Any code that saves or reads panel state from a callback or a `quitApplication` script job.

## Examples

The rebuild check that fixed the grey tab:

```python
def panel_in_control(panel_name, control_name):
    if not panel_exists(panel_name):
        return False
    return cmds.panel(panel_name, query=True, control=True).startswith(control_name + "|")
```

The build order that keeps the layout inside the workspace panel:

```python
layout = cmds.paneLayout(configuration="single")   # made while the workspace panel is the parent
if panel_exists(panel_name):
    cmds.deleteUI(panel_name, panel=True)          # resets the current parent
cmds.setParent(layout)                             # make the layout current again
cmds.modelPanel(panel_name, label=label, menuBarVisible=True)
```

## Related

- `docs/technical/camera-monitor.md`: how the monitor is built and restored, and its known quirks.
- `docs/solutions/developer-experience/headless-maya-qt-smoke-tests-with-mayapy.md`: what the headless smoke tests can and cannot cover for these panels.
- #22: the camera monitor work this came from. The fixes are in PR #23.
