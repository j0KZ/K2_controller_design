"""Tests for volume.py - Volume control action and session cache."""

import time
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from dataclasses import dataclass

from k2deck.actions.volume import SessionCache, VolumeAction


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""
    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestSessionCache:
    """Test SessionCache class."""

    def test_init_default_interval(self):
        """Cache should have default refresh interval."""
        cache = SessionCache()
        assert cache._refresh_interval == 5.0

    def test_init_custom_interval(self):
        """Cache should accept custom refresh interval."""
        cache = SessionCache(refresh_interval=10.0)
        assert cache._refresh_interval == 10.0

    def test_invalidate_resets_timestamp(self):
        """invalidate() should reset last refresh time."""
        cache = SessionCache()
        cache._last_refresh = 1000.0

        cache.invalidate()

        assert cache._last_refresh == 0.0

    @patch('k2deck.actions.volume.AudioUtilities')
    @patch('k2deck.actions.volume.pythoncom')
    def test_get_sessions_returns_empty_list_for_unknown_process(self, mock_com, mock_audio):
        """Should return empty list for unknown process."""
        mock_audio.GetAllSessions.return_value = []
        cache = SessionCache()

        result = cache.get_sessions("nonexistent.exe")

        assert result == []

    @patch('k2deck.actions.volume.AudioUtilities')
    @patch('k2deck.actions.volume.pythoncom')
    def test_get_sessions_case_insensitive(self, mock_com, mock_audio):
        """Process lookup should be case insensitive."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.Process.name.return_value = "Spotify.exe"
        mock_audio.GetAllSessions.return_value = [mock_session]

        cache = SessionCache()

        # Lookup with different case
        result = cache.get_sessions("SPOTIFY.EXE")

        # Should find it (stored as lowercase)
        assert len(result) == 1

    @patch('k2deck.actions.volume.AudioUtilities')
    @patch('k2deck.actions.volume.pythoncom')
    def test_cache_reuses_within_interval(self, mock_com, mock_audio):
        """Cache should not refresh within interval."""
        mock_audio.GetAllSessions.return_value = []
        cache = SessionCache(refresh_interval=5.0)

        # First call refreshes
        cache.get_sessions("test.exe")
        first_call_count = mock_audio.GetAllSessions.call_count

        # Second call within interval should not refresh
        cache.get_sessions("test.exe")
        second_call_count = mock_audio.GetAllSessions.call_count

        assert first_call_count == second_call_count

    @patch('k2deck.actions.volume.AudioUtilities')
    @patch('k2deck.actions.volume.pythoncom')
    def test_cache_refreshes_after_interval(self, mock_com, mock_audio):
        """Cache should refresh after interval expires."""
        mock_audio.GetAllSessions.return_value = []
        cache = SessionCache(refresh_interval=0.01)  # Very short interval

        cache.get_sessions("test.exe")
        first_call_count = mock_audio.GetAllSessions.call_count

        time.sleep(0.02)  # Wait for interval to expire

        cache.get_sessions("test.exe")
        second_call_count = mock_audio.GetAllSessions.call_count

        assert second_call_count > first_call_count


class TestVolumeAction:
    """Test VolumeAction class."""

    @patch('k2deck.actions.volume.set_master_volume')
    @patch('k2deck.actions.volume.set_process_volume')
    def test_only_triggers_on_cc(self, mock_process_vol, mock_master_vol):
        """Should only execute on CC events."""
        action = VolumeAction({"target_process": "__master__"})

        # note_on should do nothing
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
        action.execute(event)
        assert not mock_master_vol.called
        assert not mock_process_vol.called

        # note_off should do nothing
        event = MidiEvent(type="note_off", channel=16, note=36, cc=None, value=0, timestamp=0.0)
        action.execute(event)
        assert not mock_master_vol.called

    @patch('k2deck.actions.volume.set_master_volume')
    def test_maps_midi_0_to_volume_0(self, mock_master):
        """MIDI value 0 should map to volume 0.0."""
        action = VolumeAction({"target_process": "__master__"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=0, timestamp=0.0)

        action.execute(event)

        mock_master.assert_called_once_with(0.0)

    @patch('k2deck.actions.volume.set_master_volume')
    def test_maps_midi_127_to_volume_1(self, mock_master):
        """MIDI value 127 should map to volume 1.0."""
        action = VolumeAction({"target_process": "__master__"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=127, timestamp=0.0)

        action.execute(event)

        mock_master.assert_called_once_with(1.0)

    @patch('k2deck.actions.volume.set_master_volume')
    def test_maps_midi_64_to_volume_half(self, mock_master):
        """MIDI value 64 should map to ~50% volume."""
        action = VolumeAction({"target_process": "__master__"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=64, timestamp=0.0)

        action.execute(event)

        # 64/127 ≈ 0.504
        args = mock_master.call_args[0]
        assert 0.50 <= args[0] <= 0.51

    @patch('k2deck.actions.volume.set_master_volume')
    @patch('k2deck.actions.volume.set_process_volume')
    def test_uses_master_volume_for_master_target(self, mock_process, mock_master):
        """Should use set_master_volume for __master__ target."""
        action = VolumeAction({"target_process": "__master__"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=64, timestamp=0.0)

        action.execute(event)

        assert mock_master.called
        assert not mock_process.called

    @patch('k2deck.actions.volume.set_master_volume')
    @patch('k2deck.actions.volume.set_process_volume')
    def test_uses_process_volume_for_specific_process(self, mock_process, mock_master):
        """Should use set_process_volume for specific process."""
        action = VolumeAction({"target_process": "Spotify.exe"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=64, timestamp=0.0)

        action.execute(event)

        assert mock_process.called
        assert not mock_master.called
        # Check process name was passed
        args = mock_process.call_args[0]
        assert args[0] == "Spotify.exe"

    @patch('k2deck.actions.volume.set_master_volume')
    def test_default_target_is_master(self, mock_master):
        """Default target should be __master__ if not specified."""
        action = VolumeAction({})  # No target_process
        event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=64, timestamp=0.0)

        action.execute(event)

        assert mock_master.called


class TestMidiToVolumeMapping:
    """Test MIDI value to volume mapping edge cases."""

    @patch('k2deck.actions.volume.set_master_volume')
    def test_full_range_mapping(self, mock_master):
        """Test several points across the MIDI range."""
        action = VolumeAction({"target_process": "__master__"})

        test_cases = [
            (0, 0.0),
            (1, 1/127),
            (63, 63/127),
            (64, 64/127),
            (126, 126/127),
            (127, 1.0),
        ]

        for midi_val, expected_vol in test_cases:
            mock_master.reset_mock()
            event = MidiEvent(type="cc", channel=16, note=None, cc=16, value=midi_val, timestamp=0.0)

            action.execute(event)

            actual_vol = mock_master.call_args[0][0]
            assert abs(actual_vol - expected_vol) < 0.001, \
                f"MIDI {midi_val}: expected {expected_vol}, got {actual_vol}"
