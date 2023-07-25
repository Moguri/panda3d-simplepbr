from direct.directnotify.DirectNotify import DirectNotify
from direct.directnotify.Notifier import Notifier

LOGGER = None

def get() -> Notifier:
    global LOGGER # pylint: disable=global-statement
    if LOGGER is None:
        LOGGER = DirectNotify().newCategory("simplepbr")
    return LOGGER

def info(msg: str) -> None:
    get().info(msg)

def warning(msg: str) -> None:
    get().warning(msg)
