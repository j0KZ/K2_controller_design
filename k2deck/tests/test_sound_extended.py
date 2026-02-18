"""Extended tests for sound.py - play_with_pygame, stop_playback, unsupported format."""

import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from k2deck.actions.sound import (
    SoundPlayAction,
    play_with_pygame,
    stop_playback,
)


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""

    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestPlayWithPygame:
    """Test play_with_pygame function."""

    def test_returns_false_without_pygame(self):
        """Should return False when pygame not available."""
        with patch("k2deck.actions.sound._pygame_available", False):
            result = play_with_pygame("test.mp3")
        assert result is False

    def test_plays_with_default_volume(self):
        """Should play file with default volume."""
        mock_pygame = MagicMock()

        with patch("k2deck.actions.sound._pygame_available", True):
            with patch.dict(
                sys.modules, {"pygame": mock_pygame, "pygame.mixer": mock_pygame.mixer}
            ):
                # Re-bind in module
                import k2deck.actions.sound as snd

                original = getattr(snd, "pygame", None)
                snd.pygame = mock_pygame
                try:
                    result = play_with_pygame("test.mp3")
                    assert result is True
                    mock_pygame.mixer.music.load.assert_called_once_with("test.mp3")
                    mock_pygame.mixer.music.set_volume.assert_called_once_with(1.0)
                    mock_pygame.mixer.music.play.assert_called_once()
                finally:
                    if original is None:
                        delattr(snd, "pygame")
                    else:
                        snd.pygame = original

    def test_plays_with_custom_volume(self):
        """Should play file with custom volume."""
        mock_pygame = MagicMock()

        with patch("k2deck.actions.sound._pygame_available", True):
            import k2deck.actions.sound as snd

            original = getattr(snd, "pygame", None)
            snd.pygame = mock_pygame
            try:
                result = play_with_pygame("test.mp3", volume=0.5)
                assert result is True
                mock_pygame.mixer.music.set_volume.assert_called_once_with(0.5)
            finally:
                if original is None:
                    delattr(snd, "pygame")
                else:
                    snd.pygame = original

    def test_returns_false_on_error(self):
        """Should return False on playback error."""
        mock_pygame = MagicMock()
        mock_pygame.mixer.music.load.side_effect = Exception("file error")

        with patch("k2deck.actions.sound._pygame_available", True):
            import k2deck.actions.sound as snd

            original = getattr(snd, "pygame", None)
            snd.pygame = mock_pygame
            try:
                result = play_with_pygame("bad.mp3")
                assert result is False
            finally:
                if original is None:
                    delattr(snd, "pygame")
                else:
                    snd.pygame = original


class TestStopPlaybackExtended:
    """Test stop_playback edge cases."""

    def test_stops_both_winsound_and_pygame(self):
        """Should stop both winsound and pygame."""
        mock_pygame = MagicMock()

        with patch("k2deck.actions.sound._pygame_available", True):
            with patch("k2deck.actions.sound.winsound") as mock_winsound:
                import k2deck.actions.sound as snd

                original = getattr(snd, "pygame", None)
                snd.pygame = mock_pygame
                try:
                    stop_playback()
                    mock_winsound.PlaySound.assert_called_once()
                    mock_pygame.mixer.music.stop.assert_called_once()
                finally:
                    if original is None:
                        delattr(snd, "pygame")
                    else:
                        snd.pygame = original

    def test_handles_winsound_error(self):
        """Should continue even if winsound fails."""
        mock_pygame = MagicMock()

        with patch("k2deck.actions.sound._pygame_available", True):
            with patch("k2deck.actions.sound.winsound") as mock_winsound:
                mock_winsound.PlaySound.side_effect = Exception("winsound error")
                import k2deck.actions.sound as snd

                original = getattr(snd, "pygame", None)
                snd.pygame = mock_pygame
                try:
                    stop_playback()  # should not raise
                    mock_pygame.mixer.music.stop.assert_called_once()
                finally:
                    if original is None:
                        delattr(snd, "pygame")
                    else:
                        snd.pygame = original

    def test_handles_pygame_error(self):
        """Should continue even if pygame fails."""
        mock_pygame = MagicMock()
        mock_pygame.mixer.music.stop.side_effect = Exception("pygame error")

        with patch("k2deck.actions.sound._pygame_available", True):
            with patch("k2deck.actions.sound.winsound"):
                import k2deck.actions.sound as snd

                original = getattr(snd, "pygame", None)
                snd.pygame = mock_pygame
                try:
                    stop_playback()  # should not raise
                finally:
                    if original is None:
                        delattr(snd, "pygame")
                    else:
                        snd.pygame = original


class TestSoundPlayActionExtended:
    """Test SoundPlayAction edge cases."""

    @patch("k2deck.actions.sound.Path")
    def test_unsupported_format(self, mock_path):
        """Should warn on unsupported audio format."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.suffix = ".aac"

        action = SoundPlayAction({"file": "test.aac"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.sound.play_wav") as mock_wav:
            with patch("k2deck.actions.sound.play_with_pygame") as mock_pg:
                action.execute(event)
                mock_wav.assert_not_called()
                mock_pg.assert_not_called()

    @patch("k2deck.actions.sound.Path")
    @patch("k2deck.actions.sound.play_with_pygame")
    def test_ogg_uses_pygame(self, mock_pygame, mock_path):
        """Should use pygame for OGG files."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.suffix = ".ogg"
        mock_pygame.return_value = True

        action = SoundPlayAction({"file": "test.ogg", "volume": 50})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)
        mock_pygame.assert_called_once()
        assert mock_pygame.call_args[0][1] == 0.5

    @patch("k2deck.actions.sound.Path")
    @patch("k2deck.actions.sound.play_with_pygame")
    def test_flac_uses_pygame(self, mock_pygame, mock_path):
        """Should use pygame for FLAC files."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.suffix = ".flac"
        mock_pygame.return_value = True

        action = SoundPlayAction({"file": "test.flac"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)
        mock_pygame.assert_called_once()
