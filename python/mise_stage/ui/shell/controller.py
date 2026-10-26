"""Opens, fills and closes the shell panel. The only place the view meets Maya."""
from PySide6 import QtWidgets
from shiboken6 import wrapInstance

from mise_stage.dcc import workspace

from . import model
from .view import ShellView

# Keeps the widget alive; Python would otherwise free it while the panel is open.
_view = None


def show():
    """Create the panel, or fill it if it is empty and bring it to the front."""
    if not workspace.exists(model.CONTROL_NAME):
        workspace.create(model.CONTROL_NAME, model.TITLE, model.REBUILD_PATH)
        return
    rebuild()
    workspace.raise_panel(model.CONTROL_NAME)


def rebuild():
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
    layout = container.layout() or QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(_view)


def exit_shell():
    """File > Exit: close the panel. Maya keeps running."""
    workspace.close(model.CONTROL_NAME)
