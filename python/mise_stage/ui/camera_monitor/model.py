"""Identity of the camera monitor panel, passed to the Maya adapter as plain values."""

TITLE = "Camera Monitor"

# Maya control name of the panel (the saved layout refers to it, so do not rename lightly).
CONTROL_NAME = "miseStageCameraMonitorWorkspaceControl"

PANEL_NAME = "miseStageCameraMonitorPanel"
BLOCKER_NAME = "miseStageCameraMonitorInputBlocker"
PREF_NAME = "miseStageCameraMonitorState"
CAMERA = "persp"

REBUILD_PATH = "mise_stage.ui.camera_monitor.controller.rebuild"
VISIBLE_CHANGE_PATH = "mise_stage.ui.camera_monitor.controller.visible_changed"
SAVE_STATE_PATH = "mise_stage.ui.camera_monitor.controller.save_state"
