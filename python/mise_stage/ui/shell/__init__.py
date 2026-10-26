"""The application shell: the dockable "Mise Stage" panel that will host the tabs.

Open it from Maya's Script Editor with::

    from mise_stage.ui import shell
    shell.show()

Qt and Maya are imported inside the functions, so importing this package is cheap
and works where neither is installed.
"""


def show():
    """Open the panel, or bring the existing one to the front."""
    from . import controller

    controller.show()


def rebuild():
    """Fill the panel with the shell if it is empty. Maya's restore script calls this."""
    from . import controller

    controller.rebuild()
