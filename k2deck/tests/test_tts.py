"""Tests for tts.py - Text-to-Speech action."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from k2deck.actions.tts import TTSAction


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""

    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestTTSAction:
    """Test TTSAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = TTSAction({"text": "Hello"})

        with patch("k2deck.actions.tts.HAS_TTS", True):
            with patch.object(TTSAction, "_get_engine") as mock_engine:
                event = MidiEvent(
                    type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
                )
                action.execute(event)
                assert not mock_engine.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = TTSAction({"text": "Hello"})

        with patch("k2deck.actions.tts.HAS_TTS", True):
            with patch.object(TTSAction, "_get_engine") as mock_engine:
                event = MidiEvent(
                    type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
                )
                action.execute(event)
                assert not mock_engine.called

    def test_warns_if_no_text_configured(self):
        """Should warn if no text configured."""
        action = TTSAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.tts.HAS_TTS", True):
            with patch.object(TTSAction, "_get_engine") as mock_engine:
                action.execute(event)
                assert not mock_engine.called

    @patch("k2deck.actions.tts.HAS_TTS", False)
    def test_warns_if_pyttsx3_not_installed(self):
        """Should warn if pyttsx3 not installed."""
        action = TTSAction({"text": "Hello"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch.object(TTSAction, "_get_engine") as mock_engine:
            action.execute(event)
            assert not mock_engine.called

    @patch("k2deck.actions.tts.HAS_TTS", True)
    def test_speaks_text(self):
        """Should speak configured text."""
        mock_engine = MagicMock()
        TTSAction._engine = mock_engine

        action = TTSAction({"text": "Hello world", "rate": 200, "volume": 0.5})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_engine.setProperty.assert_any_call("rate", 200)
        mock_engine.setProperty.assert_any_call("volume", 0.5)
        mock_engine.say.assert_called_once_with("Hello world")
        mock_engine.runAndWait.assert_called_once()

        # Clean up
        TTSAction._engine = None

    @patch("k2deck.actions.tts.HAS_TTS", True)
    def test_default_rate_and_volume(self):
        """Should use default rate and volume."""
        mock_engine = MagicMock()
        TTSAction._engine = mock_engine

        action = TTSAction({"text": "Test"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_engine.setProperty.assert_any_call("rate", 150)
        mock_engine.setProperty.assert_any_call("volume", 1.0)

        # Clean up
        TTSAction._engine = None

    @patch("k2deck.actions.tts.HAS_TTS", True)
    def test_handles_engine_error(self):
        """Should handle TTS engine errors gracefully."""
        mock_engine = MagicMock()
        mock_engine.say.side_effect = Exception("TTS error")
        TTSAction._engine = mock_engine

        action = TTSAction({"text": "Test"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise
        action.execute(event)

        # Clean up
        TTSAction._engine = None
