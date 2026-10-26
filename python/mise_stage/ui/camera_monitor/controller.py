"""Opens, fills and closes the camera monitor panel. The only place the view meets Maya."""
from PySide6 import QtWidgets
from shiboken6 import wrapInstance

from mise_stage.dcc import camera_monitor, workspace

from . import model, view


def is_open():
    """True while the monitor panel exists. Closing it destroys the panel."""
    return workspace.exists(model.CONTROL_NAME)


def show():
    """Create the panel, or bring the existing one to the front."""
    if not is_open():
        workspace.create(model.CONTROL_NAME, model.TITLE, model.REBUILD_PATH)
        return
    workspace.raise_panel(model.CONTROL_NAME)


def hide():
    """Close the panel. Maya keeps running."""
    if is_open():
        workspace.close(model.CONTROL_NAME)


def rebuild():
    """Fill the panel unless it is already filled. Maya's restore script calls this.

    Maya runs it when the panel is created and again when it restores the panel, so it
    only builds a panel the workspace panel does not already hold and always re-attaches
    the callbacks.
    """
    if not camera_monitor.panel_in_control(model.PANEL_NAME, model.CONTROL_NAME):
        camera_monitor.build_panel(model.PANEL_NAME, model.TITLE, model.CAMERA)
        saved = camera_monitor.load_pref(model.PREF_NAME)
        if saved:
            camera_monitor.apply_state(model.PANEL_NAME, saved)
    workspace.set_visible_change(model.CONTROL_NAME, model.VISIBLE_CHANGE_PATH)
    camera_monitor.register_quit_job(workspace.callback_script(model.SAVE_STATE_PATH))
    _block_input()


def _block_input():
    pointer = camera_monitor.panel_pointer(model.PANEL_NAME)
    if pointer is None or view.block_input(wrapInstance(pointer, QtWidgets.QWidget)) == 0:
        camera_monitor.warn("The camera monitor could not block camera input, so it is not view-only.")


def visible_changed():
    """Maya calls this when the panel is shown, hidden, docked, floated or closed."""
    save_state()


def save_state():
    """Store the panel's display state, if the panel still exists."""
    state = camera_monitor.capture_state(model.PANEL_NAME)
    if state:
        camera_monitor.save_pref(model.PREF_NAME, state)
