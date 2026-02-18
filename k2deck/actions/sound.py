"""Sound Playback Action - Play audio files on button press.

Supports WAV files natively (no dependencies).
MP3/OGG support requires pygame (optional).
"""

import logging
import winsound
from pathlib import Path
from typing import TYPE_CHECKING

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)

# Try to import pygame for MP3 support
_pygame_available = False
try:
    import pygame.mixer

    pygame.mixer.init()
    _pygame_available = True
    logger.debug("pygame.mixer available for MP3/OGG playback")
except ImportError:
    logger.debug("pygame not installed, only WAV files supported")
except Exception as e:
    logger.warning("pygame.mixer init failed: %s", e)


def play_wav(file_path: str, async_play: bool = True) -> bool:
    """Play a WAV file using Windows native API.

    Args:
        file_path: Path to the WAV file.
        async_play: If True, play asynchronously (non-blocking).

    Returns:
        True if playback started, False on error.
    """
    try:
        flags = winsound.SND_FILENAME
        if async_play:
            flags |= winsound.SND_ASYNC
        winsound.PlaySound(file_path, flags)
        return True
    except Exception as e:
        logger.error("Failed to play WAV '%s': %s", file_path, e)
        return False


def play_with_pygame(file_path: str, volume: float = 1.0) -> bool:
    """Play audio file using pygame mixer.

    Args:
        file_path: Path to audio file (WAV, MP3, OGG).
        volume: Volume level 0.0-1.0.

    Returns:
        True if playback started, False on error.
    """
    if not _pygame_available:
        logger.warning("pygame not available for '%s'", file_path)
        return False

    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()
        return True
    except Exception as e:
        logger.error("Failed to play '%s' with pygame: %s", file_path, e)
        return False


def stop_playback() -> None:
    """Stop any currently playing audio."""
    # Stop winsound
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass

    # Stop pygame if available
    if _pygame_available:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


class SoundPlayAction(Action):
    """Play an audio file.

    Config options:
        file: Path to audio file (required)
        volume: Volume 0-100 (default: 100)
        stop_others: Stop other sounds before playing (default: False)

    Supported formats:
        - WAV: Always supported (Windows native)
        - MP3, OGG: Requires pygame

    Config example:
    {
        "action": "sound_play",
        "file": "C:/sounds/alert.wav",
        "volume": 80
    }
    """

    def __init__(self, config: dict):
        """Initialize sound play action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._file = config.get("file", "")
        self._volume = config.get("volume", 100) / 100.0  # Convert to 0-1
        self._stop_others = config.get("stop_others", False)

    def execute(self, event: "MidiEvent") -> None:
        """Play the configured sound.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._file:
            logger.warning("SoundPlayAction: no file configured")
            return

        # Validate file exists
        path = Path(self._file)
        if not path.exists():
            logger.warning("Sound file not found: %s", self._file)
            return

        # Stop other sounds if requested
        if self._stop_others:
            stop_playback()

        # Choose playback method based on file extension
        ext = path.suffix.lower()

        if ext == ".wav":
            # Use native Windows API for WAV (fast, no dependencies)
            success = play_wav(str(path))
        elif ext in (".mp3", ".ogg", ".flac"):
            # Use pygame for other formats
            success = play_with_pygame(str(path), self._volume)
        else:
            logger.warning("Unsupported audio format: %s", ext)
            return

        if success:
            logger.debug(
                "Playing sound: %s (volume: %d%%)", path.name, int(self._volume * 100)
            )


class SoundStopAction(Action):
    """Stop all currently playing sounds.

    Config example:
    {
        "action": "sound_stop"
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Stop all sounds.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        stop_playback()
        logger.debug("Stopped all sounds")
