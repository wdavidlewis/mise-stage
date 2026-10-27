"""The shell widget: a menu bar over a blank body that later work fills with tabs."""
from PySide6 import QtCore, QtGui, QtWidgets

from . import model


class ShellView(QtWidgets.QMainWindow):
    """The shell's main window, with File and Camera menus.

    Signals:
        exit_requested: File > Exit was chosen.
        camera_monitor_toggled: Camera > Camera Monitor was checked (True) or
            unchecked (False) by the user.
        camera_menu_about_to_show: The Camera menu is about to open.
    """

    exit_requested = QtCore.Signal()
    camera_monitor_toggled = QtCore.Signal(bool)
    camera_menu_about_to_show = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(model.OBJECT_NAME)
        self.setWindowTitle(model.TITLE)

        # Parent each menu explicitly: a menu made by addMenu(title) is freed with its Python wrapper.
        file_menu = QtWidgets.QMenu("&File", self)
        self.menuBar().addMenu(file_menu)
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.exit_requested.emit)

        camera_menu = QtWidgets.QMenu("&Camera", self)
        self.menuBar().addMenu(camera_menu)
        camera_menu.aboutToShow.connect(self.camera_menu_about_to_show.emit)
        # Parent the action explicitly too: in Maya the wrapper of addAction(text) is freed while the menu keeps its own.
        self._camera_monitor_action = QtGui.QAction("Camera &Monitor", self)
        self._camera_monitor_action.setCheckable(True)
        camera_menu.addAction(self._camera_monitor_action)
        self._camera_monitor_action.triggered.connect(self._on_camera_monitor_triggered)

        self.setCentralWidget(QtWidgets.QWidget())

    def _on_camera_monitor_triggered(self, checked: bool) -> None:
        # Connect a method, not signal.emit: PySide would call emit without the check state.
        self.camera_monitor_toggled.emit(checked)

    def set_camera_monitor_checked(self, checked: bool) -> None:
        """Set the Camera Monitor check mark. Only the user triggering the item emits a signal.

        Args:
            checked: True to show the item as checked.
        """
        self._camera_monitor_action.setChecked(checked)
