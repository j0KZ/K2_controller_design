"""System actions - Lock, screenshot, etc."""

import ctypes
import logging
import subprocess
from typing import TYPE_CHECKING

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


def lock_workstation() -> bool:
    """Lock the Windows workstation."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return True
    except Exception as e:
        logger.error("Failed to lock workstation: %s", e)
        return False


def take_screenshot() -> bool:
    """Take a screenshot using Windows Snipping Tool."""
    try:
        # Win+Shift+S opens Snip & Sketch
        subprocess.Popen(["explorer", "ms-screenclip:"])
        return True
    except Exception as e:
        logger.error("Failed to take screenshot: %s", e)
        return False


def open_task_manager() -> bool:
    """Open Windows Task Manager."""
    try:
        subprocess.Popen(["taskmgr"])
        return True
    except Exception as e:
        logger.error("Failed to open Task Manager: %s", e)
        return False


def open_settings() -> bool:
    """Open Windows Settings."""
    try:
        subprocess.Popen(["explorer", "ms-settings:"])
        return True
    except Exception as e:
        logger.error("Failed to open Settings: %s", e)
        return False


class SystemAction(Action):
    """Action for system-level commands.

    Config options:
        command: One of "lock", "screenshot", "taskmanager", "settings".
    """

    COMMANDS = {
        "lock": lock_workstation,
        "screenshot": take_screenshot,
        "taskmanager": open_task_manager,
        "task_manager": open_task_manager,
        "settings": open_settings,
    }

    def execute(self, event: "MidiEvent") -> None:
        """Execute system command on Note On."""
        if event.type != "note_on" or event.value == 0:
            return

        command = self.config.get("command", "").lower()

        if command not in self.COMMANDS:
            logger.warning("Unknown system command: %s", command)
            return

        try:
            self.COMMANDS[command]()
            logger.info("Executed system command: %s", command)
        except Exception as e:
            logger.error("SystemAction error: %s", e)


class NoopAction(Action):
    """Placeholder action that does nothing.

    Used for explicitly mapped but not-yet-implemented controls.
    Suppresses "unmapped control" log messages.
    """

    def execute(self, event: "MidiEvent") -> None:
        """Do nothing."""
        pass
