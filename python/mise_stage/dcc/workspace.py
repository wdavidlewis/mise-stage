"""Maya workspace panels: the dockable containers the UI is built into.

Maya imports are deferred into the functions that need them, so
``restore_script`` can be imported and tested outside Maya.
"""

_RESTORE_TEMPLATE = """\
try:
    import importlib
    _rebuild = getattr(importlib.import_module({module!r}), {function!r})
except ImportError as _error:
    import maya.cmds
    maya.cmds.warning(
        "mise-stage could not load {module}: %s. "
        "Put mise-stage's python/ folder on sys.path before Maya starts." % _error
    )
else:
    _rebuild()
"""


def restore_script(rebuild_path):
    """Return the script Maya re-runs to rebuild a panel's contents.

    Maya runs it at startup, before any mise-stage code is on the path, so the
    import guard has to live in the script itself. Only ``ImportError`` is
    caught; an error raised by the rebuild function is a bug and surfaces.

    ``rebuild_path`` is the dotted path of the rebuild function, e.g.
    ``"mise_stage.ui.shell.rebuild"``.
    """
    module, _, function = rebuild_path.rpartition(".")
    return _RESTORE_TEMPLATE.format(module=module, function=function)


def exists(name):
    """True when a workspace panel called ``name`` exists."""
    import maya.cmds as cmds

    return bool(cmds.workspaceControl(name, query=True, exists=True))


def create(name, label, rebuild_path):
    """Create the panel, floating, and have Maya fill it through the restore script."""
    import maya.cmds as cmds

    cmds.workspaceControl(
        name,
        label=label,
        retain=False,
        floating=True,
        uiScript=restore_script(rebuild_path),
    )


def raise_panel(name):
    """Show the panel and bring it to the front, as a docked tab or a floating window."""
    import maya.cmds as cmds

    cmds.workspaceControl(name, edit=True, restore=True)


def close(name):
    """Close the panel. Maya itself keeps running."""
    import maya.cmds as cmds

    cmds.workspaceControl(name, edit=True, close=True)


def container_pointer(name):
    """Return the panel's Qt container as an int pointer, or None if there is none."""
    import maya.OpenMayaUI as omui

    pointer = omui.MQtUtil.findControl(name)
    return int(pointer) if pointer else None
