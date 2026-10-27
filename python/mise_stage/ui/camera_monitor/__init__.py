"""The camera monitor: a view-only Maya panel that looks through the persp camera.

Open it from Maya's Script Editor with::

    from mise_stage.ui import camera_monitor
    camera_monitor.show()

Qt and Maya are imported inside the functions, so importing this package is cheap
and works where neither is installed.
"""


def show() -> None:
    """Open the panel, or bring the existing one to the front."""
    from . import controller

    controller.show()


def hide() -> None:
    """Close the panel."""
    from . import controller

    controller.hide()


def is_open() -> bool:
    """True while the panel exists.

    Returns:
        Whether the panel exists.
    """
    from . import controller

    return controller.is_open()


def rebuild() -> None:
    """Fill the panel if it is empty. Maya's restore script calls this."""
    from . import controller

    controller.rebuild()
