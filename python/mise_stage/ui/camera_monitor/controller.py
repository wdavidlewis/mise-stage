"""Opens, fills and closes the camera monitor panel."""
from PySide6 import QtWidgets
from shiboken6 import wrapInstance

from mise_stage.dcc import camera_monitor, workspace

from . import model, view


def is_open() -> bool:
    """True while the monitor panel exists. Closing it destroys the panel.

    Returns:
        Whether the monitor panel exists.
    """
    return workspace.exists(model.CONTROL_NAME)


def show() -> None:
    """Create the panel, or bring the existing one to the front."""
    if not is_open():
        workspace.create(model.CONTROL_NAME, model.TITLE, model.REBUILD_PATH)
        return
    workspace.raise_panel(model.CONTROL_NAME)


def hide() -> None:
    """Close the panel."""
    if is_open():
        workspace.close(model.CONTROL_NAME)


def rebuild() -> None:
    """Fill the panel unless it is already filled. Maya's restore script calls this.

    Maya runs it when the panel is created and again when it restores the panel, so it
    only builds a panel the workspace panel does not already hold and always re-attaches
    the callbacks. The saved look is restored last, so a look that fails to apply cannot
    leave the monitor interactive.
    """
    built = not camera_monitor.panel_in_control(model.PANEL_NAME, model.CONTROL_NAME)
    if built:
        camera_monitor.build_panel(model.PANEL_NAME, model.TITLE, model.CAMERA)
    workspace.set_visible_change(model.CONTROL_NAME, model.VISIBLE_CHANGE_PATH)
    camera_monitor.register_quit_job(workspace.callback_script(model.SAVE_STATE_PATH))
    _block_input()
    if built:
        _restore_state()


def _restore_state() -> None:
    """Apply the saved look to the panel. A failure is reported as a warning."""
    saved = camera_monitor.load_pref(model.PREF_NAME)
    if not saved:
        return
    try:
        camera_monitor.apply_state(model.PANEL_NAME, saved)
    except RuntimeError as error:
        camera_monitor.warn("The camera monitor could not restore its saved look (%s); using the default look." % error)


def _block_input() -> None:
    """Make the panel's viewports ignore input. Warns if they cannot be blocked."""
    pointer = workspace.container_pointer(model.PANEL_NAME)
    if pointer is None or view.block_input(wrapInstance(pointer, QtWidgets.QWidget)) == 0:
        camera_monitor.warn("The camera monitor could not block camera input, so it is not view-only.")


def visible_changed() -> None:
    """Maya calls this when the panel is shown, hidden, docked, floated or closed."""
    save_state()


def save_state() -> None:
    """Store the panel's display state, if the monitor's workspace panel still holds it.

    A closed monitor can leave its model panel behind with no parent. That panel is never
    read: asking it for its state while Maya quits crashed Maya.
    """
    if not camera_monitor.panel_in_control(model.PANEL_NAME, model.CONTROL_NAME):
        return
    state = camera_monitor.capture_state(model.PANEL_NAME)
    if state:
        camera_monitor.save_pref(model.PREF_NAME, state)
