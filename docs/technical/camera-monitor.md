# Camera monitor

The camera monitor is a Maya panel that shows the view through the persp camera. It is view-only and keeps its shading and lighting separate from every other view. It floats, or docks as a tab beside the Attribute Editor, the Mise Stage panel or any other Maya panel, and Maya remembers where you leave it.

For now it always looks through persp, so it is effectively a second persp view with its own display settings. Later work points it at the Active camera and uses its settings for renders.

## Opening it

Choose **Camera ▸ Camera Monitor** on the Mise Stage shell. The item is checked while the monitor is open: checking it opens the monitor, and unchecking it closes it. The check is read from the monitor's real state each time the menu opens, so it is right after you close the monitor with its own close button, dock it, or restart Maya.

The Camera menu is on the shell, so the shell has to be open to use it. Closing the shell with File ▸ Exit leaves an open monitor open. You can also open and close it from the Script Editor (Python tab):

```python
from mise_stage.ui import camera_monitor

camera_monitor.show()  # opens it, or brings the existing one to the front
camera_monitor.hide()  # closes it
camera_monitor.is_open()
```

The first time it opens it floats.

## What it shows

- The view through persp. Mise adds no camera, constraint or other node to your scene.
- A smooth shaded view with Maya's default lighting. A new Maya model panel starts in wireframe, so the monitor sets its own starting look.
- The **Shading**, **Lighting**, **Show**, **Renderer** and **Help** menus. Use them to change the monitor's look; they do not change any other view.
- No **View** menu and no icon bar. Both hold camera controls (Select Camera, Frame Selection, bookmarks, camera tools), and the monitor looks through the same camera you work in.

## View-only

The monitor ignores mouse, mouse wheel, tablet and keyboard input on its 3D view. You cannot tumble, track or dolly it, click to select, or use a camera hotkey such as F in it. Selection made in other views still shows highlighted.

Maya runs a hotkey on the panel under the pointer, but the key press goes to whichever widget has keyboard focus. So while the pointer is over the monitor's 3D view, keys are ignored for the whole application, and they work again as soon as the pointer leaves.

## Display settings

The monitor saves its display state when it is shown, hidden, docked, floated or closed, and when Maya quits, and restores it the next time it opens. The state is Maya's own editor state string, stored in one Maya preference, `miseStageCameraMonitorState`, so it is local to your machine and your Maya preferences.

Because it is the whole editor state, it also keeps other display toggles you set, such as the grid. Where these settings live permanently is decided with the user settings system (#20) and the scene settings system (#21); the stored value then moves there.

## Restoring it when Maya starts

If the monitor was open when Maya last exited, Maya rebuilds it at startup in the same place, with the same look. A monitor you closed stays closed. Restore works the same way as the shell's, and needs `python/` on Maya's `sys.path` at startup (see [Application shell](shell.md)). If the package cannot be imported, Maya shows an empty "Camera Monitor" tab and the Script Editor gets one warning.

## Maya workspaces

Maya keeps panel layout per workspace (Modeling, Animation and so on). A monitor opened in one workspace does not appear in another until you open it there, and the Camera menu check reflects the workspace you are in.

## Reloading during development

Close the monitor, reload the modules in this order, then open it again:

```python
import importlib

import mise_stage.dcc.camera_monitor
import mise_stage.dcc.workspace
import mise_stage.ui.camera_monitor
import mise_stage.ui.camera_monitor.controller
import mise_stage.ui.camera_monitor.model
import mise_stage.ui.camera_monitor.view
import mise_stage.ui.shell.controller

mise_stage.ui.camera_monitor.hide()

for module in (
    mise_stage.dcc.workspace,
    mise_stage.dcc.camera_monitor,
    mise_stage.ui.camera_monitor.model,
    mise_stage.ui.camera_monitor.view,
    mise_stage.ui.camera_monitor.controller,
    mise_stage.ui.camera_monitor,
    mise_stage.ui.shell.controller,  # holds the monitor's functions for the Camera menu
):
    importlib.reload(module)

mise_stage.ui.camera_monitor.show()
```

If you changed the shell's view, close the shell and reload the shell modules first (see [Application shell](shell.md)).

## Behavior confirmed in Maya 2026

Checked by hand when the monitor was built:

- A model panel inside a Maya workspace panel floats and docks as a tab beside the Attribute Editor, and both positions survive a Maya restart. The monitor comes back in the same tab group with the same look.
- A new model panel's own menu bar holds View, Shading, Renderer, Lighting, Show and Help. There is no Panels menu, so there is no tear-off or panel-swap item to remove. The View menu and the icon bar can be hidden.
- Tumble, track, dolly, wheel, click selection, marquee and F do nothing in the monitor, and work normally in the persp view.
- The panel's visible-change callback fires when the panel is docked, floated, closed and when Maya quits, and the display state can still be read at that moment. The close callback never fired, so only the visible-change callback is used.
- Callback scripts are Python, not MEL.
- The editor state string restores a rebuilt panel exactly, and a preference variable survives a restart.
- The Camera Monitor item follows the monitor after its own close button.
- File ▸ Exit on the shell leaves the monitor open.

## Known quirks

- The Maya ViewCube (the front, right, top cube) sometimes appears in the monitor after you close it from the Camera menu and reopen it. It is not part of the saved display state and Maya has no per-panel switch for it that was found. It cannot be clicked, because the monitor ignores input, so it is cosmetic.
- Closing a workspace panel destroys it, but its model panel can survive with no parent. The monitor treats a model panel as built only when it sits inside the monitor's own workspace panel, and rebuilds otherwise. It also never reads such a left-behind panel: the quit-time save did, with the monitor closed, and Maya crashed while quitting.
- Input is blocked once, when the panel is built, on the viewports found then. After a Maya restart the viewport was found on the first try, so there is no retry. If it is ever missing, the monitor warns in the Script Editor that it is not view-only. Decided in the review of PR #23.

## How it is built

The code follows the layers in the [README](../../README.md):

- `python/mise_stage/dcc/camera_monitor.py` builds the model panel, hides the View menu and icon bar, and reads, applies and stores the display state, with `maya.cmds`. It imports no Qt and does not import `ui/`. `python/mise_stage/dcc/workspace.py` supplies the panel create, close and restore helpers shared with the shell, plus the callback script.
- `python/mise_stage/ui/camera_monitor/` holds the Qt side. `model.py` has the names, `view.py` the input blocker, and `controller.py` the `show`, `hide`, `is_open` and `rebuild` logic.
- The panel is created floating with `retain=False` and a restore script that calls `mise_stage.ui.camera_monitor.controller.rebuild()`. Maya runs that script when it creates and when it restores the panel. `rebuild()` builds the model panel only if the monitor's workspace panel does not already hold one, re-attaches the visible-change callback and the quit-time save, and blocks input.
- The Camera menu and its check live in `python/mise_stage/ui/shell/`.

## Later work

These are not built yet. They record what a Maya 2026 spike found, so the next design starts from it.

- **Pointing the monitor at the Active camera.** A camera parent-constrained to persp tracks it and keeps its own lens. While you dolly persp, the follower moves smoothly. While you tumble, it catches up only when you release the mouse. It re-syncs the next time persp moves. A panel that looks through persp directly stays linked to the persp view.
- **Hosting.** The monitor is a workspace panel by decision. The main view layout can also hold a model panel, and a plain Qt window cannot. See [where a Maya model panel can live](../solutions/developer-experience/maya-model-panel-hosting-options.md).
