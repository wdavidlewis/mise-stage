---
title: Blocking a Maya viewport needs an application-wide key filter for hotkeys
date: 2026-10-26
category: developer-experience
module: ui/camera_monitor
problem_type: developer_experience
component: frontend
severity: medium
applies_when:
  - Making a Maya model panel view-only so it cannot move a camera or change the selection
  - Installing a Qt event filter on a Maya 3D viewport widget
  - Blocking a Maya hotkey for a single panel
symptoms:
  - An event filter on the viewport stops mouse, wheel and click input but pressing F still frames the camera
  - Keyboard input never reaches the filter installed on the viewport
root_cause: wrong_api
resolution_type: code_fix
retire_when: Autodesk documents or changes how Maya routes hotkeys to the panel under the pointer, observed on Maya 2026. Recheck by hovering a view-only panel, pressing a camera hotkey with an object selected, and watching whether the shared camera moves.
tags: [maya, qt, event-filter, hotkeys, viewport, qmayaglwidget, view-only]
---

# Blocking a Maya viewport needs an application-wide key filter for hotkeys

## Context

The camera monitor (#22) must not let the artist move a camera or change the selection through it. It looks through the same camera as the persp view, so any tumble, dolly or framing done in the monitor would move the working view. An event filter on the monitor's viewport widget blocked every mouse, wheel, tablet and click event. Pressing F with the pointer over the monitor still framed the shared camera.

## Guidance

**Filter the viewport for pointer input.** The viewport is the Qt widget whose class name is `QmayaGLWidget` (`python/mise_stage/ui/camera_monitor/view.py:7`). An event filter installed on it that swallows mouse press, release, double-click, move, wheel, tablet and context-menu events stops tumble, track, dolly, wheel zoom, click selection, marquee and right-click menus (`view.py:15-25`, `view.py:63`).

**Keys do not reach that filter.** A key press goes to the widget with keyboard focus, and the viewport was never that widget (Maya's own widget reported a focus policy of no focus when queried in Maya 2026, before our code set it). Maya applied the hotkey to the panel the pointer was over while the key event went to another widget, which is why a filter on the viewport never saw it. That mechanism is inferred from the behavior, not read from Maya's internals; the evidence is that swallowing keys application-wide while the pointer was over the monitor stopped F there and left it working over the persp view.

**Swallow keys application-wide, only while the pointer is over the viewport.** The viewport's own filter does see the pointer enter and leave, so use those two events to install and remove a second filter on the application that swallows `KeyPress`, `KeyRelease` and `ShortcutOverride` (`view.py:9-13`, `view.py:28-48`). Installing it only while the pointer is inside keeps the cost of a Python filter on every event bounded to the time the artist is over the monitor.

Costs and limits to know about:

- While the pointer rests on the monitor, no hotkey works anywhere in Maya, and typing into a field elsewhere does nothing.
- If the viewport is hidden or reparented under the pointer and no Leave event arrives, keys can stay swallowed until the pointer enters and leaves again. Not observed in Maya, but reviewers flagged it and nothing handles it.
- The key filter is a child of the input blocker, which is a child of the panel, so destroying the panel destroys the filter.

## Why This Matters

A view-only panel that looks through a shared camera is only view-only if every route to that camera is closed. The pointer routes are easy to close and the hotkey route is not visible from the widget you are filtering. Without the key filter the monitor passed a hands-on check of mouse input and still moved the working camera on F.

## When to Apply

- Any Maya panel that must not change the scene, the selection or a shared camera.
- Any Qt filter on a Maya viewport that is expected to stop keyboard shortcuts.

## Examples

The pointer-driven install and removal:

```python
def eventFilter(self, watched, event):
    kind = event.type()
    if kind == QtCore.QEvent.Enter:
        QtWidgets.QApplication.instance().installEventFilter(self._keys)
    elif kind == QtCore.QEvent.Leave:
        QtWidgets.QApplication.instance().removeEventFilter(self._keys)
    return kind in _BLOCKED
```

Confirming it: select an object, park the shared camera away from it, hover the monitor and press F, then hover the normal persp view and press F. The camera should move only for the second. The first attempt at this test selected nothing, so F had nothing to frame and the test proved nothing.

## Related

- `docs/solutions/developer-experience/maya-model-panel-outlives-closed-workspace-panel.md`: lifecycle gotchas for the same panel.
- `docs/technical/camera-monitor.md`: the monitor's view-only behavior as shipped.
- #22: the camera monitor work this came from. The fix is on branch `22-camera-monitor`; the pull request is not open yet.
