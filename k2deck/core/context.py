"""Context utilities - Foreground app detection with caching."""

import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import psutil
import win32gui
import win32process

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class AppInfo:
    """Information about an application."""

    name: str  # Process name (e.g., "Spotify.exe")
    title: str  # Window title
    pid: int  # Process ID
    hwnd: int  # Window handle


class ContextCache:
    """Cache for context information to avoid frequent system calls.

    win32gui + psutil calls take ~5-10ms each. This cache reduces
    the frequency of these calls by caching the foreground app info.
    """

    def __init__(self, refresh_interval: float = 0.1):
        """Initialize context cache.

        Args:
            refresh_interval: Seconds between cache refreshes (default 100ms).
        """
        self._foreground_app: AppInfo | None = None
        self._last_refresh = 0.0
        self._refresh_interval = refresh_interval
        self._lock = threading.Lock()
        self._running_apps: dict[str, list[int]] = {}  # name -> list of PIDs
        self._running_apps_refresh = 0.0
        self._running_apps_interval = 2.0  # Refresh running apps every 2s

    def get_foreground_app(self) -> AppInfo | None:
        """Get the currently focused application.

        Returns:
            AppInfo for the foreground app, or None if detection fails.
        """
        with self._lock:
            now = time.monotonic()
            if now - self._last_refresh > self._refresh_interval:
                self._refresh_foreground()
            return self._foreground_app

    def _refresh_foreground(self) -> None:
        """Refresh the foreground app cache."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                self._foreground_app = None
                return

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            try:
                process = psutil.Process(pid)
                name = process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                name = ""

            self._foreground_app = AppInfo(
                name=name,
                title=title,
                pid=pid,
                hwnd=hwnd,
            )
            self._last_refresh = time.monotonic()
            logger.debug("Foreground app: %s (%s)", name, title[:50] if title else "")

        except Exception as e:
            logger.error("Failed to get foreground app: %s", e)
            self._foreground_app = None

    def is_app_focused(self, app_name: str) -> bool:
        """Check if a specific app has focus.

        Args:
            app_name: Process name to check (case-insensitive).
                      Can be partial match (e.g., "spotify" matches "Spotify.exe").

        Returns:
            True if the app is focused, False otherwise.
        """
        app = self.get_foreground_app()
        if not app:
            return False

        app_name_lower = app_name.lower()
        return app_name_lower in app.name.lower()

    def is_app_running(self, app_name: str) -> bool:
        """Check if a specific app is running.

        Args:
            app_name: Process name to check (case-insensitive).

        Returns:
            True if the app is running, False otherwise.
        """
        with self._lock:
            now = time.monotonic()
            if now - self._running_apps_refresh > self._running_apps_interval:
                self._refresh_running_apps()

            app_name_lower = app_name.lower()
            for name in self._running_apps:
                if app_name_lower in name.lower():
                    return True
            return False

    def _refresh_running_apps(self) -> None:
        """Refresh the running apps cache."""
        try:
            self._running_apps.clear()
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = proc.info["name"]
                    pid = proc.info["pid"]
                    if name:
                        name_lower = name.lower()
                        if name_lower not in self._running_apps:
                            self._running_apps[name_lower] = []
                        self._running_apps[name_lower].append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self._running_apps_refresh = time.monotonic()
            logger.debug("Refreshed running apps cache: %d processes", len(self._running_apps))

        except Exception as e:
            logger.error("Failed to refresh running apps: %s", e)

    def invalidate(self) -> None:
        """Force cache refresh on next access."""
        with self._lock:
            self._last_refresh = 0.0
            self._running_apps_refresh = 0.0


# Global context cache instance
_context_cache = ContextCache()


def get_foreground_app() -> AppInfo | None:
    """Get the currently focused application.

    Returns:
        AppInfo for the foreground app, or None if detection fails.
    """
    return _context_cache.get_foreground_app()


def is_app_focused(app_name: str) -> bool:
    """Check if a specific app has focus.

    Args:
        app_name: Process name to check (case-insensitive, partial match).

    Returns:
        True if the app is focused, False otherwise.
    """
    return _context_cache.is_app_focused(app_name)


def is_app_running(app_name: str) -> bool:
    """Check if a specific app is running.

    Args:
        app_name: Process name to check (case-insensitive, partial match).

    Returns:
        True if the app is running, False otherwise.
    """
    return _context_cache.is_app_running(app_name)


def invalidate_context_cache() -> None:
    """Force context cache refresh."""
    _context_cache.invalidate()
