"""Spotify actions - Control Spotify via Web API.

Uses Windows SendInput API for media key fallback when API is unavailable.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core import keyboard
from k2deck.core.spotify_client import spotify

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


def _media_key_fallback(key_name: str) -> bool:
    """Send media key as fallback when API fails.

    Uses SendInput API for reliable media key simulation.
    """
    try:
        if keyboard.tap_key(key_name, hold_ms=15):
            logger.info("Media key sent: %s", key_name)
            return True
        else:
            logger.error("Failed to send media key: %s", key_name)
            return False
    except Exception as e:
        logger.error("Media key failed: %s", e)
        return False


class SpotifyPlayPauseAction(Action):
    """Toggle Spotify play/pause using media key for instant response."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        # Media key = instant response (no API latency)
        _media_key_fallback("media_play_pause")
        logger.info("Spotify: play/pause")


class SpotifyNextAction(Action):
    """Skip to next track using media key for instant response."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        _media_key_fallback("media_next")
        logger.info("Spotify: next")


class SpotifyPreviousAction(Action):
    """Go to previous track using media key for instant response."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        _media_key_fallback("media_previous")
        logger.info("Spotify: previous")


class SpotifyLikeAction(Action):
    """Toggle like status of current track."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        if not spotify.is_ready:
            logger.warning("Spotify not connected")
            return

        result = spotify.toggle_like()
        if result is not None:
            logger.info("Spotify: track %s", "liked" if result else "unliked")


class SpotifyShuffleAction(Action):
    """Toggle shuffle mode."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        if not spotify.is_ready:
            logger.warning("Spotify not connected")
            return

        result = spotify.toggle_shuffle()
        if result is not None:
            logger.info("Spotify: shuffle %s", "on" if result else "off")


class SpotifyRepeatAction(Action):
    """Cycle through repeat modes."""

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "note_on" or event.value == 0:
            return

        if not spotify.is_ready:
            logger.warning("Spotify not connected")
            return

        result = spotify.cycle_repeat()
        if result:
            logger.info("Spotify: repeat %s", result)


class SpotifyVolumeAction(Action):
    """Spotify volume control via pycaw (Windows audio mixer).

    Uses pycaw for instant, responsive volume control.
    No API calls = no rate limits = instant feedback.

    Config options:
    - min_volume: Minimum volume (default: 0)
    - max_volume: Maximum volume (default: 100)
    """

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "cc":
            return

        try:
            from k2deck.actions.volume import set_process_volume, invalidate_session_cache

            # Map MIDI value (0-127) to volume (0.0-1.0)
            min_vol = self.config.get("min_volume", 0) / 100.0
            max_vol = self.config.get("max_volume", 100) / 100.0
            volume = min_vol + (event.value / 127.0) * (max_vol - min_vol)

            # Invalidate cache periodically to catch Spotify starting
            if event.value == 0 or event.value == 127:
                invalidate_session_cache()

            if set_process_volume("Spotify.exe", volume):
                logger.debug("Spotify volume: %.0f%%", volume * 100)
        except Exception as e:
            logger.debug("Spotify volume failed: %s", e)


class SpotifySeekAction(Action):
    """Seek in current track using encoder.

    Config options:
    - step_ms: Milliseconds to seek per encoder tick (default: 5000 = 5 seconds)
    """

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "cc":
            return

        if not spotify.is_ready:
            logger.debug("Spotify not connected, seek ignored")
            return

        step_ms = self.config.get("step_ms", 5000)
        value = event.value

        # Determine direction from encoder value
        # Two's complement: 1-63 = CW (forward), 65-127 = CCW (backward)
        if 1 <= value <= 63:
            # Clockwise = forward
            delta = step_ms * min(value, 3)  # Some acceleration
        elif 65 <= value <= 127:
            # Counter-clockwise = backward
            delta = -step_ms * min(128 - value, 3)
        else:
            return

        spotify.seek_relative(delta)
        logger.debug("Spotify: seek %+d ms", delta)


class SpotifyPrevNextAction(Action):
    """Encoder-based prev/next track control using media keys.

    CW = next track, CCW = previous track.
    Includes debounce to prevent multiple skips on fast rotation.
    """

    _last_skip_time: float = 0
    _debounce_ms: float = 300  # Minimum time between skips

    def execute(self, event: "MidiEvent") -> None:
        if event.type != "cc":
            return

        import time

        now = time.time() * 1000
        if now - self._last_skip_time < self._debounce_ms:
            return

        value = event.value

        if 1 <= value <= 63:
            # Clockwise = next
            _media_key_fallback("media_next")
            logger.debug("Spotify: next")
            self._last_skip_time = now
        elif 65 <= value <= 127:
            # Counter-clockwise = previous
            _media_key_fallback("media_previous")
            logger.debug("Spotify: previous")
            self._last_skip_time = now
