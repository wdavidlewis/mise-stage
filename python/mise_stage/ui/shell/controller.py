"""Opens, fills and closes the shell panel. The only place the view meets Maya."""
from PySide6 import QtWidgets
from shiboken6 import wrapInstance

from mise_stage.dcc import workspace
from mise_stage.ui import camera_monitor

from . import model
from .view import ShellView

# Keeps the widget alive; Python would otherwise free it while the panel is open.
_view: ShellView | None = None


def show() -> None:
    """Create the panel, or fill it if it is empty and bring it to the front."""
    if not workspace.exists(model.CONTROL_NAME):
        workspace.create(model.CONTROL_NAME, model.TITLE, model.REBUILD_PATH)
        return
    rebuild()
    workspace.raise_panel(model.CONTROL_NAME)


def rebuild() -> None:
    """Add the shell to the panel unless the panel already holds one."""
    global _view

    pointer = workspace.container_pointer(model.CONTROL_NAME)
    if pointer is None:
        return
    container = wrapInstance(pointer, QtWidgets.QWidget)
    # Ask the live container, not _view: Maya may have deleted the widget _view points at.
    if container.findChild(QtWidgets.QWidget, model.OBJECT_NAME) is not None:
        return

    _view = ShellView()
    _view.exit_requested.connect(exit_shell)
    _view.camera_monitor_toggled.connect(set_camera_monitor_open)
    _view.camera_menu_about_to_show.connect(
        lambda view=_view: view.set_camera_monitor_checked(camera_monitor.is_open())
    )
    layout = container.layout() or QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(_view)


def set_camera_monitor_open(open_: bool) -> None:
    """Camera > Camera Monitor: open the monitor when checked, close it when unchecked.

    Args:
        open_: True when the menu item is checked, False when it is unchecked.
    """
    if open_:
        camera_monitor.show()
    else:
        camera_monitor.hide()


def exit_shell() -> None:
    """File > Exit: close the panel. Maya keeps running."""
    workspace.close(model.CONTROL_NAME)
