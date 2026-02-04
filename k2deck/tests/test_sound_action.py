"""Tests for sound.py - Sound playback actions."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from pathlib import Path

from k2deck.actions.sound import (
    SoundPlayAction,
    SoundStopAction,
    play_wav,
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


class TestPlayWav:
    """Test play_wav function."""

    @patch('k2deck.actions.sound.winsound')
    def test_plays_wav_async(self, mock_winsound):
        """Should play WAV file asynchronously by default."""
        result = play_wav("C:/test/sound.wav")

        assert result is True
        mock_winsound.PlaySound.assert_called_once()
        call_args = mock_winsound.PlaySound.call_args
        assert call_args[0][0] == "C:/test/sound.wav"
        # Check flags include ASYNC
        flags = call_args[0][1]
        assert flags & mock_winsound.SND_ASYNC

    @patch('k2deck.actions.sound.winsound')
    def test_plays_wav_sync(self, mock_winsound):
        """Should play WAV file synchronously when async_play=False."""
        # Set up real flag values for proper testing
        mock_winsound.SND_FILENAME = 0x00020000
        mock_winsound.SND_ASYNC = 0x0001

        result = play_wav("C:/test/sound.wav", async_play=False)

        assert result is True
        mock_winsound.PlaySound.assert_called_once()
        call_args = mock_winsound.PlaySound.call_args
        flags = call_args[0][1]
        # Should only have FILENAME flag, not ASYNC
        assert flags == mock_winsound.SND_FILENAME

    @patch('k2deck.actions.sound.winsound')
    def test_returns_false_on_error(self, mock_winsound):
        """Should return False if playback fails."""
        mock_winsound.PlaySound.side_effect = Exception("Playback error")

        result = play_wav("C:/test/sound.wav")

        assert result is False


class TestStopPlayback:
    """Test stop_playback function."""

    @patch('k2deck.actions.sound.winsound')
    def test_stops_winsound(self, mock_winsound):
        """Should stop winsound playback."""
        stop_playback()

        mock_winsound.PlaySound.assert_called_once_with(
            None, mock_winsound.SND_PURGE
        )


class TestSoundPlayAction:
    """Test SoundPlayAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = SoundPlayAction({"file": "test.wav"})

        with patch('k2deck.actions.sound.play_wav') as mock_play:
            event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
            action.execute(event)
            assert not mock_play.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = SoundPlayAction({"file": "test.wav"})

        with patch('k2deck.actions.sound.play_wav') as mock_play:
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)
            action.execute(event)
            assert not mock_play.called

    def test_warns_if_no_file_configured(self):
        """Should warn if no file configured."""
        action = SoundPlayAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        with patch('k2deck.actions.sound.play_wav') as mock_play:
            action.execute(event)
            assert not mock_play.called

    @patch('k2deck.actions.sound.Path')
    @patch('k2deck.actions.sound.play_wav')
    def test_plays_wav_file(self, mock_play, mock_path):
        """Should play WAV file using native API."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.suffix = ".wav"
        mock_play.return_value = True

        action = SoundPlayAction({"file": "C:/sounds/alert.wav"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        action.execute(event)

        mock_play.assert_called_once()

    @patch('k2deck.actions.sound.Path')
    @patch('k2deck.actions.sound.play_with_pygame')
    def test_plays_mp3_with_pygame(self, mock_pygame, mock_path):
        """Should play MP3 file using pygame."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.suffix = ".mp3"
        mock_pygame.return_value = True

        action = SoundPlayAction({"file": "C:/sounds/alert.mp3", "volume": 80})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        action.execute(event)

        mock_pygame.assert_called_once()
        # Volume should be converted to 0-1 range (passed as positional arg)
        call_args = mock_pygame.call_args[0]
        assert call_args[1] == 0.8

    @patch('k2deck.actions.sound.Path')
    def test_warns_if_file_not_found(self, mock_path):
        """Should warn if file doesn't exist."""
        mock_path.return_value.exists.return_value = False

        action = SoundPlayAction({"file": "C:/sounds/missing.wav"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        with patch('k2deck.actions.sound.play_wav') as mock_play:
            action.execute(event)
            assert not mock_play.called

    @patch('k2deck.actions.sound.Path')
    @patch('k2deck.actions.sound.stop_playback')
    @patch('k2deck.actions.sound.play_wav')
    def test_stop_others_stops_before_play(self, mock_play, mock_stop, mock_path):
        """Should stop other sounds before playing if stop_others=True."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.suffix = ".wav"
        mock_play.return_value = True

        action = SoundPlayAction({"file": "test.wav", "stop_others": True})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        action.execute(event)

        mock_stop.assert_called_once()
        mock_play.assert_called_once()


class TestSoundStopAction:
    """Test SoundStopAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = SoundStopAction({})

        with patch('k2deck.actions.sound.stop_playback') as mock_stop:
            event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
            action.execute(event)
            assert not mock_stop.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = SoundStopAction({})

        with patch('k2deck.actions.sound.stop_playback') as mock_stop:
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)
            action.execute(event)
            assert not mock_stop.called

    @patch('k2deck.actions.sound.stop_playback')
    def test_stops_all_sounds(self, mock_stop):
        """Should stop all sounds."""
        action = SoundStopAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        action.execute(event)

        mock_stop.assert_called_once()
