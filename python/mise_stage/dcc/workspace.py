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


_CALLBACK_TEMPLATE = """\
try:
    import importlib
    _callback = getattr(importlib.import_module({module!r}), {function!r})
except ImportError:
    pass  # the restore script has already warned that the package is not on sys.path
else:
    _callback()
"""


def callback_script(function_path):
    """Return the script Maya runs for a panel callback such as visible-change.

    ``function_path`` is the dotted path of the function to call, e.g.
    ``"mise_stage.ui.camera_monitor.controller.visible_changed"``. Maya can run the
    callback before the package is importable, so a missing package is skipped quietly;
    an error raised by the function itself is a bug and surfaces.
    """
    module, _, function = function_path.rpartition(".")
    return _CALLBACK_TEMPLATE.format(module=module, function=function)


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


def create(name, label, rebuild_path, visible_change_path=None):
    """Create the panel, floating, and have Maya fill it through the restore script.

    ``visible_change_path`` is the dotted path of a function Maya calls whenever the
    panel is shown, hidden, docked, floated or closed.
    """
    import maya.cmds as cmds

    options = {}
    if visible_change_path:
        options["visibleChangeCommand"] = callback_script(visible_change_path)
    cmds.workspaceControl(
        name,
        label=label,
        retain=False,
        floating=True,
        uiScript=restore_script(rebuild_path),
        **options,
    )


def set_visible_change(name, function_path):
    """Attach the visible-change callback to an existing panel.

    Maya rebuilds a restored panel by re-running its restore script, not ``create``,
    so the rebuild function calls this to attach the callback again.
    """
    import maya.cmds as cmds

    cmds.workspaceControl(name, edit=True, visibleChangeCommand=callback_script(function_path))


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
