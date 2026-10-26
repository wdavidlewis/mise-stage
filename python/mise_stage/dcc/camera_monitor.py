"""The camera monitor panel's Maya side: the model panel, its menus, and its saved look.

Maya imports are deferred into the functions that need them, so this module can be
imported and tested outside Maya. Names (panel, preference) are passed in by the caller.
"""

_quit_job = None


def panel_exists(panel_name):
    """True when the model panel called ``panel_name`` exists."""
    import maya.cmds as cmds

    return bool(cmds.modelPanel(panel_name, query=True, exists=True))


def panel_in_control(panel_name, control_name):
    """True when the model panel exists and sits inside the workspace panel ``control_name``.

    Closing a workspace panel destroys it but can leave its model panel behind with no
    parent, so the panel existing is not enough to say the workspace panel is filled.
    """
    import maya.cmds as cmds

    if not panel_exists(panel_name):
        return False
    return cmds.panel(panel_name, query=True, control=True).startswith(control_name + "|")


def build_panel(panel_name, label, camera):
    """Fill the current workspace panel with a model panel looking through ``camera``.

    A panel left over under the same name is removed, so a repeated or failed build
    cannot collide with it. The new panel opens smooth shaded with default lighting
    (Maya's own new-panel look is wireframe) and keeps only the menus that change the
    look; the camera-changing View menu and the icon bar are hidden.
    """
    import maya.cmds as cmds

    # Create the layout first: deleting a UI element resets the parent Maya builds into
    # (to the Script Editor), so the layout is made current again after the delete.
    layout = cmds.paneLayout(configuration="single")
    if panel_exists(panel_name):
        cmds.deleteUI(panel_name, panel=True)
    cmds.setParent(layout)
    cmds.modelPanel(panel_name, label=label, menuBarVisible=True)
    cmds.modelPanel(panel_name, edit=True, camera=camera)

    editor = cmds.modelPanel(panel_name, query=True, modelEditor=True)
    cmds.modelEditor(editor, edit=True, displayAppearance="smoothShaded", displayLights="default")
    _hide_camera_controls(panel_name)


def _hide_camera_controls(panel_name):
    import maya.cmds as cmds

    view_menus = [m for m in cmds.lsUI(menus=True, long=True) if panel_name in m and m.split("|")[-1] == "View"]
    if view_menus:
        cmds.menu(view_menus[0], edit=True, visible=False)
    else:
        warn("The camera monitor could not find its View menu to hide, so it can be pointed at another camera.")
    cmds.layout(cmds.modelPanel(panel_name, query=True, barLayout=True), edit=True, visible=False)


def capture_state(panel_name):
    """Return Maya's string for restoring the panel's display state, or None if it is gone."""
    import maya.cmds as cmds

    if not panel_exists(panel_name):
        return None
    editor = cmds.modelPanel(panel_name, query=True, modelEditor=True)
    return cmds.modelEditor(editor, query=True, stateString=True)


def apply_state(panel_name, state):
    """Restore a display state returned by ``capture_state`` onto the panel."""
    import maya.cmds as cmds
    import maya.mel as mel

    editor = cmds.modelPanel(panel_name, query=True, modelEditor=True)
    mel.eval(state.replace("$editorName", editor))


def save_pref(name, value):
    """Store a string in Maya's own preferences, which survive a restart."""
    import maya.cmds as cmds

    cmds.optionVar(stringValue=(name, value))


def load_pref(name):
    """Return the stored string, or None if nothing has been stored."""
    import maya.cmds as cmds

    return cmds.optionVar(query=name) if cmds.optionVar(exists=name) else None


def register_quit_job(script):
    """Run ``script`` when Maya quits. Calling this again leaves exactly one job."""
    global _quit_job
    import maya.cmds as cmds

    if _quit_job is not None and cmds.scriptJob(exists=_quit_job):
        return
    _quit_job = cmds.scriptJob(event=["quitApplication", script])


def warn(message):
    """Print a one-line warning in the Script Editor."""
    import maya.cmds as cmds

    cmds.warning(message)
