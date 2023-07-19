from direct.directnotify.DirectNotify import DirectNotify
from direct.directnotify.Notifier import Notifier

logger = None

def get() -> Notifier:
    global logger
    if logger is None:
        logger = DirectNotify().newCategory("simplepbr")
    return logger

def info(*args) -> None:
    get().info(*args)

def warning(*args) -> None:
    get().warning(*args)
