"""System actions - Lock, screenshot, power commands, URL, clipboard."""

import ctypes
import logging
import subprocess
import webbrowser
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


def sleep_computer() -> bool:
    """Put the computer to sleep."""
    try:
        # SetSuspendState(hibernate, force, wakeup_events)
        ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        return True
    except Exception as e:
        logger.error("Failed to sleep: %s", e)
        return False


def hibernate_computer() -> bool:
    """Hibernate the computer."""
    try:
        ctypes.windll.powrprof.SetSuspendState(1, 1, 0)
        return True
    except Exception as e:
        logger.error("Failed to hibernate: %s", e)
        return False


def shutdown_computer(force: bool = False) -> bool:
    """Shutdown the computer.

    Args:
        force: If True, force shutdown without waiting for apps to close.
    """
    try:
        cmd = ["shutdown", "/s", "/t", "0"]
        if force:
            cmd.append("/f")
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        logger.error("Failed to shutdown: %s", e)
        return False


def restart_computer(force: bool = False) -> bool:
    """Restart the computer.

    Args:
        force: If True, force restart without waiting for apps to close.
    """
    try:
        cmd = ["shutdown", "/r", "/t", "0"]
        if force:
            cmd.append("/f")
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        logger.error("Failed to restart: %s", e)
        return False


def open_url(url: str) -> bool:
    """Open a URL in the default browser.

    Args:
        url: URL to open.

    Returns:
        True if successful, False if URL is invalid or failed.
    """
    from urllib.parse import urlparse

    # Validate URL scheme to prevent file://, javascript://, etc.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning("Blocked non-HTTP URL: %s (scheme: %s)", url, parsed.scheme)
            return False
    except Exception as e:
        logger.warning("Invalid URL: %s - %s", url, e)
        return False

    try:
        webbrowser.open(url)
        logger.info("Opened URL: %s", url)
        return True
    except Exception as e:
        logger.error("Failed to open URL: %s", e)
        return False


def paste_to_clipboard(text: str) -> bool:
    """Copy text to clipboard and paste it.

    Args:
        text: Text to paste.
    """
    try:
        import win32clipboard
        import win32con

        # Copy to clipboard with proper resource cleanup
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        logger.debug("Copied to clipboard (%d chars)", len(text))
        return True
    except Exception as e:
        logger.error("Failed to copy to clipboard: %s", e)
        return False


class SystemAction(Action):
    """Action for system-level commands.

    Config options:
        command: One of "lock", "screenshot", "taskmanager", "settings",
                 "sleep", "hibernate", "shutdown", "restart".
        force: For shutdown/restart, force close apps (default: False).
    """

    COMMANDS = {
        "lock": lock_workstation,
        "screenshot": take_screenshot,
        "taskmanager": open_task_manager,
        "task_manager": open_task_manager,
        "settings": open_settings,
        "sleep": sleep_computer,
        "hibernate": hibernate_computer,
    }

    def execute(self, event: "MidiEvent") -> None:
        """Execute system command on Note On."""
        if event.type != "note_on" or event.value == 0:
            return

        command = self.config.get("command", "").lower()
        force = self.config.get("force", False)

        # Handle shutdown/restart with force parameter
        if command == "shutdown":
            shutdown_computer(force=force)
            logger.info("Executed system command: shutdown (force=%s)", force)
            return
        elif command == "restart":
            restart_computer(force=force)
            logger.info("Executed system command: restart (force=%s)", force)
            return

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


class OpenURLAction(Action):
    """Open a URL in the default browser.

    Config options:
        url: The URL to open.

    Config example:
    {
        "name": "Open GitHub",
        "action": "open_url",
        "url": "https://github.com"
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Open URL on Note On."""
        if event.type != "note_on" or event.value == 0:
            return

        url = self.config.get("url", "")
        if not url:
            logger.warning("OpenURLAction: No URL configured")
            return

        open_url(url)


class ClipboardPasteAction(Action):
    """Copy predefined text to clipboard.

    Config options:
        text: The text to copy to clipboard.
        paste: If True, also simulate Ctrl+V after copying (default: False).

    Config example:
    {
        "name": "Paste Email",
        "action": "clipboard_paste",
        "text": "user@example.com",
        "paste": true
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Copy text to clipboard on Note On."""
        if event.type != "note_on" or event.value == 0:
            return

        text = self.config.get("text", "")
        if not text:
            logger.warning("ClipboardPasteAction: No text configured")
            return

        if not paste_to_clipboard(text):
            return

        # Optionally paste with Ctrl+V
        if self.config.get("paste", False):
            import time

            from k2deck.core import keyboard

            time.sleep(0.05)  # Small delay for clipboard to be ready
            keyboard.execute_hotkey(["ctrl", "v"], hold_ms=20)
            logger.info("Pasted text (%d chars)", len(text))
