"""Window actions - Focus and launch apps using pywin32."""

import logging
import time
from typing import TYPE_CHECKING

import win32con
import win32gui
import win32process

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


def find_window_by_process(process_name: str) -> int | None:
    """Find a window handle by process name.

    Args:
        process_name: Process name (e.g., "Spotify.exe", "Discord.exe")

    Returns:
        Window handle (hwnd) or None if not found.
    """
    process_name_lower = process_name.lower()
    result = None

    def enum_callback(hwnd: int, _) -> bool:
        nonlocal result
        if not win32gui.IsWindowVisible(hwnd):
            return True

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            import psutil

            proc = psutil.Process(pid)
            if proc.name().lower() == process_name_lower:
                # Prefer windows with titles (main windows)
                title = win32gui.GetWindowText(hwnd)
                if title:
                    result = hwnd
                    return False  # Stop enumeration
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
    except Exception as e:
        logger.debug("EnumWindows stopped: %s", e)

    return result


def focus_window(hwnd: int) -> bool:
    """Bring a window to foreground.

    Args:
        hwnd: Window handle.

    Returns:
        True if successful.
    """
    try:
        # If minimized, restore it
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Bring to foreground
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.warning("Failed to focus window: %s", e)
        return False


def focus_app(process_name: str) -> bool:
    """Focus an application by process name.

    Args:
        process_name: Process name (e.g., "Spotify.exe")

    Returns:
        True if app was focused successfully.
    """
    hwnd = find_window_by_process(process_name)
    if hwnd:
        return focus_window(hwnd)
    else:
        logger.warning("Could not find window for: %s", process_name)
        return False


class FocusAction(Action):
    """Action that focuses an application window.

    Config example:
    {
        "name": "Focus Spotify",
        "action": "focus",
        "target_app": "Spotify.exe"
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Focus the target application."""
        if event.type == "note_on" and event.value == 0:
            return  # Ignore note off

        target = self.config.get("target_app")
        if not target:
            logger.warning("FocusAction missing target_app")
            return

        name = self.config.get("name", target)
        if focus_app(target):
            logger.info("Focused: %s", name)
        else:
            logger.warning("Could not focus: %s", name)


class LaunchAction(Action):
    """Action that launches or focuses an application.

    Config example:
    {
        "name": "Launch Spotify",
        "action": "launch",
        "target_app": "Spotify.exe",
        "launch_path": "C:/Users/.../Spotify.exe"
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Launch or focus the target application."""
        if event.type == "note_on" and event.value == 0:
            return

        target = self.config.get("target_app")
        if not target:
            logger.warning("LaunchAction missing target_app")
            return

        # Try to focus first
        if focus_app(target):
            logger.info("Focused existing: %s", target)
            return

        # If not running, try to launch
        launch_path = self.config.get("launch_path")
        if launch_path:
            import subprocess

            try:
                subprocess.Popen(launch_path, shell=True)
                logger.info("Launched: %s", launch_path)
            except Exception as e:
                logger.error("Failed to launch %s: %s", launch_path, e)
        else:
            logger.warning("App not running and no launch_path: %s", target)
