"""The input blocker that keeps the camera monitor view-only."""
from PySide6 import QtCore, QtWidgets

from . import model

# Maya's 3D viewport widget class; the monitor's menus sit outside it and stay usable.
_VIEWPORT_CLASS = "QmayaGLWidget"

_BLOCKED = {
    QtCore.QEvent.MouseButtonPress,
    QtCore.QEvent.MouseButtonRelease,
    QtCore.QEvent.MouseButtonDblClick,
    QtCore.QEvent.MouseMove,
    QtCore.QEvent.Wheel,
    QtCore.QEvent.KeyPress,
    QtCore.QEvent.KeyRelease,
    QtCore.QEvent.ShortcutOverride,
    QtCore.QEvent.ContextMenu,
    QtCore.QEvent.TabletPress,
    QtCore.QEvent.TabletRelease,
    QtCore.QEvent.TabletMove,
}


class InputBlocker(QtCore.QObject):
    """Swallows mouse, wheel, tablet and key input; paint and resize pass through."""

    def eventFilter(self, watched, event):
        return event.type() in _BLOCKED


def block_input(panel):
    """Make every 3D viewport in ``panel`` ignore input, and return how many were found.

    Safe to call again on a panel that is already blocked.
    """
    viewports = [w for w in panel.findChildren(QtWidgets.QWidget) if w.metaObject().className() == _VIEWPORT_CLASS]
    blocker = panel.findChild(InputBlocker, model.BLOCKER_NAME)
    if blocker is None:
        blocker = InputBlocker(panel)
        blocker.setObjectName(model.BLOCKER_NAME)
    for viewport in viewports:
        viewport.installEventFilter(blocker)
        viewport.setFocusPolicy(QtCore.Qt.NoFocus)
    return len(viewports)
