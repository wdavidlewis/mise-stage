"""The shell widget: a menu bar over a blank body that later work fills with tabs."""
from PySide6 import QtCore, QtWidgets

from . import model


class ShellView(QtWidgets.QMainWindow):
    exit_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName(model.OBJECT_NAME)
        self.setWindowTitle(model.TITLE)

        # Parent the menu explicitly: a menu made by addMenu(title) is freed with its Python wrapper.
        file_menu = QtWidgets.QMenu("&File", self)
        self.menuBar().addMenu(file_menu)
        exit_action = file_menu.addAction("E&xit")
        exit_action.triggered.connect(self.exit_requested.emit)

        self.setCentralWidget(QtWidgets.QWidget())
