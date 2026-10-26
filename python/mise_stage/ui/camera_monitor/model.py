"""Identity of the camera monitor panel, passed to the Maya adapter as plain values."""

TITLE = "Camera Monitor"

# Maya control name of the panel (the saved layout refers to it, so do not rename lightly).
CONTROL_NAME = "miseStageCameraMonitorWorkspaceControl"

# Name of the model panel inside it.
PANEL_NAME = "miseStageCameraMonitorPanel"

# Qt object name of the input blocker, used to tell whether the viewport is already blocked.
BLOCKER_NAME = "miseStageCameraMonitorInputBlocker"

# Maya preference holding the panel's display state between sessions.
PREF_NAME = "miseStageCameraMonitorState"

# The camera the monitor looks through. Later work replaces this with the Active camera.
CAMERA = "persp"

# Dotted paths Maya's scripts call. Like the shell's, they name the controller, not the lazy
# package functions, so loading Qt happens inside the script's import guard.
REBUILD_PATH = "mise_stage.ui.camera_monitor.controller.rebuild"
VISIBLE_CHANGE_PATH = "mise_stage.ui.camera_monitor.controller.visible_changed"
SAVE_STATE_PATH = "mise_stage.ui.camera_monitor.controller.save_state"
