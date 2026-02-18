"""Volume action - Per-app volume control using pycaw."""

import logging
import threading
import time
from ctypes import POINTER, cast
from typing import TYPE_CHECKING

import pythoncom
from comtypes import CLSCTX_ALL
from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume,
    ISimpleAudioVolume,
)

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class SessionCache:
    """Cache for audio sessions to avoid frequent enumeration."""

    def __init__(self, refresh_interval: float = 5.0):
        """Initialize session cache.

        Args:
            refresh_interval: Seconds between cache refreshes.
        """
        self._cache: dict[str, list] = {}
        self._last_refresh = 0.0
        self._refresh_interval = refresh_interval
        self._lock = threading.Lock()

    def get_sessions(self, process_name: str) -> list:
        """Get audio sessions for a process.

        Args:
            process_name: Name of process (e.g., "Spotify.exe").

        Returns:
            List of matching audio sessions.
        """
        with self._lock:
            now = time.monotonic()
            if now - self._last_refresh > self._refresh_interval:
                self._refresh_cache()

            return self._cache.get(process_name.lower(), [])

    def _refresh_cache(self) -> None:
        """Refresh the session cache."""
        self._cache.clear()
        try:
            pythoncom.CoInitialize()
            try:
                sessions = AudioUtilities.GetAllSessions()
                for session in sessions:
                    if session.Process:
                        name = session.Process.name().lower()
                        if name not in self._cache:
                            self._cache[name] = []
                        self._cache[name].append(session)
                self._last_refresh = time.monotonic()
                logger.debug(
                    "Refreshed audio session cache: %d processes", len(self._cache)
                )
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            logger.error("Failed to refresh session cache: %s", e)

    def invalidate(self) -> None:
        """Force cache refresh on next access."""
        with self._lock:
            self._last_refresh = 0.0


# Global session cache
_session_cache = SessionCache()


def set_process_volume(process_name: str, volume: float) -> bool:
    """Set volume for a specific process.

    Args:
        process_name: Process name (e.g., "Spotify.exe").
        volume: Volume level 0.0 to 1.0.

    Returns:
        True if volume was set, False otherwise.
    """
    sessions = _session_cache.get_sessions(process_name)

    if not sessions:
        logger.debug("No audio session for: %s", process_name)
        return False

    success = False
    try:
        pythoncom.CoInitialize()
        try:
            for session in sessions:
                try:
                    volume_interface = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume_interface.SetMasterVolume(volume, None)
                    success = True
                except Exception as e:
                    logger.error("Failed to set volume for %s: %s", process_name, e)
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        logger.error("COM error for %s: %s", process_name, e)

    return success


def set_master_volume(volume: float) -> bool:
    """Set system master volume.

    Args:
        volume: Volume level 0.0 to 1.0.

    Returns:
        True if volume was set, False otherwise.
    """
    try:
        pythoncom.CoInitialize()
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL,
                None,
            )
            volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            volume_interface.SetMasterVolumeLevelScalar(volume, None)
            return True
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        logger.error("Failed to set master volume: %s", e)
        return False


def get_master_volume() -> float | None:
    """Get current system master volume.

    Returns:
        Volume level 0.0 to 1.0, or None on error.
    """
    try:
        pythoncom.CoInitialize()
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL,
                None,
            )
            volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            return volume_interface.GetMasterVolumeLevelScalar()
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        logger.error("Failed to get master volume: %s", e)
        return None


class VolumeAction(Action):
    """Action for controlling per-app or master volume.

    Config options:
        target_process: Process name (e.g., "Spotify.exe") or "__master__".
    """

    def execute(self, event: "MidiEvent") -> None:
        """Set volume based on CC value (0-127 -> 0.0-1.0)."""
        if event.type != "cc":
            return

        target = self.config.get("target_process", "__master__")
        volume = event.value / 127.0

        try:
            if target == "__master__":
                set_master_volume(volume)
                logger.debug("Master volume: %.0f%%", volume * 100)
            else:
                if set_process_volume(target, volume):
                    logger.debug("%s volume: %.0f%%", target, volume * 100)
        except Exception as e:
            logger.error("VolumeAction error: %s", e)


def invalidate_session_cache() -> None:
    """Force session cache refresh (call when apps open/close)."""
    _session_cache.invalidate()
