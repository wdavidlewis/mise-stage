---
title: Where a Maya model panel can live: a workspace panel or the main layout, not a plain Qt window
date: 2026-10-26
category: developer-experience
module: ui/shell
problem_type: developer_experience
component: frontend
severity: medium
applies_when:
  - Deciding where a Maya model panel (`cmds.modelPanel`) should sit in the UI
  - Considering putting a model panel inside a Qt widget you create yourself, such as the shell's body
symptoms:
  - Moving a model panel into a Qt window fails with a name-lookup error
  - The area the panel was moved into stays empty and grey
  - A widget is deleted while the panel is being moved into it
root_cause: unknown
resolution_type: design_decision
retire_when: Recheck in a later Maya release by reparenting a model panel into a QWidget and by setting a model panel into MainPane|viewPanes. The Qt attempts failed in one spike run and their cause was not recorded.
tags: [maya, modelpanel, hosting, qt, paneLayout, workspacecontrol]
---

# Where a Maya model panel can live: a workspace panel or the main layout, not a plain Qt window

## Context

The camera monitor (#22) is a model panel. Its first design question was where it should be hosted. The shell is a Qt window, so the first idea was to put the monitor inside the shell's body. A throwaway Maya 2026 spike, run on 2026-10-26, tested the options. This note records what was observed so the design choice is not repeated.

## Guidance

**A plain Qt window does not work for hosting a model panel.** Three attempts to put a model panel inside a Qt widget that Mise Stage creates failed:

- Looking the panel up by name in the Qt widget raised a name-lookup error.
- After the panel was moved into the widget, the area stayed empty and grey, with no 3D view.
- Moving the panel while a widget was being replaced deleted the widget.

The spike did not record why these failed, so treat the cause as unknown.

**A model panel works inside a Maya workspace panel.** Create the panel in a `workspaceControl` whose restore script builds it, as the camera monitor does (`python/mise_stage/dcc/workspace.py`). It floats, docks as a tab beside the Attribute Editor, and keeps its position across restarts. This is the path the camera monitor ships with, and it avoids the Qt attempts above.

**A model panel also works in Maya's main view layout.** Maya's main window has a layout named `MainPane|viewPanes`, with stock model panels `modelPanel1` to `modelPanel4` in it. A custom model panel can be placed into one of its slots:

```python
cmds.paneLayout("MainPane|viewPanes", edit=True, setPane=(panel, index))
```

The panel was live there. Its display settings (`modelEditor` appearance, lights and shadows) did not affect the stock panels. The spike did not ship this, and the decision was to leave it for later work.

## Why This Matters

Choosing the wrong host costs a lot of time in Maya, where the failures are silent (an empty grey area) or crash-prone. A plain Qt window looks like the natural home for a Qt-based shell, but for a Maya model panel it is not.

## When to Apply

- Before placing any `cmds`-built panel (model panel, outliner, script editor panel) in the UI.
- Before wrapping a Maya panel in a widget that Mise Stage creates.

## Examples

The hosting the camera monitor uses (`python/mise_stage/dcc/workspace.py`):

```python
cmds.workspaceControl(
    name,
    label=label,
    retain=False,
    floating=True,
    uiScript=restore_script(rebuild_path),
)
```

The restore script then builds the model panel inside the control (`python/mise_stage/dcc/camera_monitor.py`, `build_panel`).
