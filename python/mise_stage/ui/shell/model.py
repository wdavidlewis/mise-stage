"""Identity of the shell panel, passed to the Maya adapter as plain values."""

TITLE = "Mise Stage"

# Maya control name of the panel (the saved layout refers to it, so do not rename lightly).
CONTROL_NAME = "miseStageShellWorkspaceControl"

# Qt object name of the shell widget, used to tell whether the panel is already filled.
OBJECT_NAME = "miseStageShell"

# Dotted path Maya's restore script calls to rebuild the panel's contents. It names the
# controller, not the lazy shell.rebuild(), so loading the controller and Qt happens inside
# the script's import guard and a failure there is a warning, not a traceback.
REBUILD_PATH = "mise_stage.ui.shell.controller.rebuild"
