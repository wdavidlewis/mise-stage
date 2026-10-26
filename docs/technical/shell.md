# Application shell

The shell is the "Mise Stage" panel in Maya 2026+. It is a native Maya workspace panel, so it docks like the Attribute Editor: as a tab, split beside another panel, or floating as its own window. Maya remembers where it was left and reopens it there on the next launch. Today it holds a File menu with Exit and a blank body; later work adds tabs to it.

In these docs the **shell** is the Qt widget (menu bar and body) and the **panel** is the Maya workspace container it sits in.

## Opening it

Run this in the Script Editor (Python tab), or put it on a shelf button:

```python
from mise_stage.ui import shell

shell.show()
```

`show()` creates the panel, or brings the existing one to the front. It never creates a second panel. File ▸ Exit closes the panel and leaves Maya running; `show()` brings it back where it was.

## Restoring it when Maya starts

If the panel was open when Maya last exited, Maya rebuilds it at startup by re-running a saved script. A panel closed with File ▸ Exit is not rebuilt.

Restore only works if `python/` is already on Maya's `sys.path` at startup, for example through `PYTHONPATH` in `Maya.env`. Installation tooling is tracked separately (#16).

If the package cannot be imported at startup, Maya still shows an empty "Mise Stage" tab, and the Script Editor gets one warning saying `python/` must be on `sys.path`. No traceback is printed. Once the path is set, call `shell.show()` and the empty tab is filled in place.

## Maya workspaces

Maya keeps panel layout per workspace (Modeling, Animation and so on). A panel docked in one workspace does not appear in another until you open it there with `shell.show()`.

## Reloading during development

Close the panel with File ▸ Exit, reload the modules in this order, then open it again:

```python
import importlib

import mise_stage.dcc.workspace
import mise_stage.ui.shell
import mise_stage.ui.shell.controller
import mise_stage.ui.shell.model
import mise_stage.ui.shell.view

for module in (
    mise_stage.dcc.workspace,
    mise_stage.ui.shell.model,
    mise_stage.ui.shell.view,
    mise_stage.ui.shell.controller,
    mise_stage.ui.shell,
):
    importlib.reload(module)

mise_stage.ui.shell.show()
```

## Behavior confirmed in Maya 2026

Checked by hand when the shell was built:

- The panel docks as a tab over the Attribute Editor and floats, and both positions survive a Maya restart.
- File ▸ Exit closes the panel without quitting Maya, and `shell.show()` returns it to its last position.
- A panel closed with File ▸ Exit is not rebuilt after a restart.
- A second `shell.show()` while the panel is open brings it forward and does not create another.
- With `python/` off the path at startup, the restored tab is empty and the Script Editor shows one warning, not a traceback. `shell.show()` fills it once the path is set.
- A `QMainWindow` with a menu bar renders correctly inside the panel.

Not checked: whether Maya keeps the old shell widget alive across a close and reopen. `rebuild()` therefore looks in the live panel for a shell and never relies on a stored reference.

## How it is built

The code follows the layers in the [README](../../README.md):

- `python/mise_stage/dcc/workspace.py` creates, raises and closes the panel with `maya.cmds`, and hands the panel's Qt container to the UI as a plain integer pointer. It imports no Qt and does not import `ui/`.
- `python/mise_stage/ui/shell/` holds the Qt shell. `model.py` has the panel's name and title, `view.py` the menu bar and body, and `controller.py` the `show()` and `rebuild()` logic.
- The panel is created with `retain=False` and a restore script. Maya runs that script when it restores the panel and each time the panel is reopened, and the script calls `mise_stage.ui.shell.controller.rebuild()`. `rebuild()` adds the shell only if the panel does not already hold one.
- The restore script catches only `ImportError`, and the import of the controller (and so of Qt) happens inside that guard. An error raised by `rebuild()` itself is a bug and is allowed to show.
