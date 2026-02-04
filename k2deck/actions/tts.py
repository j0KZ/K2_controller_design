"""Text-to-Speech Action - Speak text using TTS engine.

Useful for alerts, notifications, or accessibility.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)

# Optional dependency - use Windows SAPI via pyttsx3
try:
    import pyttsx3

    HAS_TTS = True
except ImportError:
    pyttsx3 = None
    HAS_TTS = False


class TTSAction(Action):
    """Speak text using text-to-speech.

    Config options:
        text: Text to speak (required)
        rate: Speech rate in words per minute (default: 150)
        volume: Volume 0.0 to 1.0 (default: 1.0)

    Config example:
    {
        "action": "tts",
        "text": "Stream starting in 5 minutes",
        "rate": 150,
        "volume": 0.8
    }
    """

    _engine = None

    def __init__(self, config: dict) -> None:
        """Initialize TTS action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._text = config.get("text", "")
        self._rate = config.get("rate", 150)
        self._volume = config.get("volume", 1.0)

    @classmethod
    def _get_engine(cls):
        """Get or create TTS engine (lazy initialization)."""
        if cls._engine is None and HAS_TTS:
            try:
                cls._engine = pyttsx3.init()
            except Exception as e:
                logger.error("Failed to initialize TTS engine: %s", e)
        return cls._engine

    def execute(self, event: "MidiEvent") -> None:
        """Speak the configured text.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not HAS_TTS:
            logger.warning("pyttsx3 not installed. Run: pip install pyttsx3")
            return

        if not self._text:
            logger.warning("TTSAction: no text configured")
            return

        engine = self._get_engine()
        if engine is None:
            logger.warning("TTSAction: TTS engine not available")
            return

        try:
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            engine.say(self._text)
            engine.runAndWait()
            logger.info("TTS: %s", self._text[:50])
        except Exception as e:
            logger.error("TTS failed: %s", e)
