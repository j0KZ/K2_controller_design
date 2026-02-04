"""Tests for audio_switch.py and audio_devices.py - Audio device switching."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from k2deck.actions.audio_switch import AudioSwitchAction, AudioListAction
from k2deck.core.audio_devices import AudioDevice, cycle_audio_devices


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""
    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestAudioDevice:
    """Test AudioDevice namedtuple."""

    def test_audio_device_creation(self):
        """Should create AudioDevice with correct fields."""
        device = AudioDevice(
            id="{0.0.0.00000000}.{abc-123}",
            name="Speakers",
            is_default=True
        )
        assert device.id == "{0.0.0.00000000}.{abc-123}"
        assert device.name == "Speakers"
        assert device.is_default is True


class TestCycleAudioDevices:
    """Test cycle_audio_devices function."""

    @patch('k2deck.core.audio_devices.get_audio_devices')
    @patch('k2deck.core.audio_devices.set_default_audio_device')
    def test_cycles_to_next_device(self, mock_set, mock_get):
        """Should cycle to the next device in the list."""
        mock_get.return_value = [
            AudioDevice(id="id1", name="Speakers", is_default=True),
            AudioDevice(id="id2", name="Headphones", is_default=False),
        ]
        mock_set.return_value = True

        result = cycle_audio_devices(["Speakers", "Headphones"])

        assert result == "Headphones"
        mock_set.assert_called_once_with("id2")

    @patch('k2deck.core.audio_devices.get_audio_devices')
    @patch('k2deck.core.audio_devices.set_default_audio_device')
    def test_cycles_back_to_first(self, mock_set, mock_get):
        """Should cycle back to first device after last."""
        mock_get.return_value = [
            AudioDevice(id="id1", name="Speakers", is_default=False),
            AudioDevice(id="id2", name="Headphones", is_default=True),
        ]
        mock_set.return_value = True

        result = cycle_audio_devices(["Speakers", "Headphones"])

        assert result == "Speakers"
        mock_set.assert_called_once_with("id1")

    @patch('k2deck.core.audio_devices.get_audio_devices')
    def test_returns_none_if_no_devices(self, mock_get):
        """Should return None if no devices found."""
        mock_get.return_value = []

        result = cycle_audio_devices(["Speakers"])

        assert result is None

    def test_returns_none_if_empty_list(self):
        """Should return None if device list is empty."""
        result = cycle_audio_devices([])

        assert result is None


class TestAudioSwitchAction:
    """Test AudioSwitchAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = AudioSwitchAction({"devices": ["Speakers"]})

        with patch('k2deck.actions.audio_switch.set_default_audio_device_by_name') as mock:
            event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
            action.execute(event)
            assert not mock.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = AudioSwitchAction({"devices": ["Speakers"]})

        with patch('k2deck.actions.audio_switch.set_default_audio_device_by_name') as mock:
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)
            action.execute(event)
            assert not mock.called

    def test_warns_if_no_devices_configured(self):
        """Should warn if no devices configured."""
        action = AudioSwitchAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        with patch('k2deck.actions.audio_switch.set_default_audio_device_by_name') as mock:
            action.execute(event)
            assert not mock.called

    @patch('k2deck.actions.audio_switch.set_default_audio_device_by_name')
    def test_single_device_switches_directly(self, mock_switch):
        """Should switch directly when only one device configured."""
        mock_switch.return_value = True

        action = AudioSwitchAction({"devices": ["Headphones"], "type": "output"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        action.execute(event)

        mock_switch.assert_called_once_with("Headphones", "output")

    @patch('k2deck.actions.audio_switch.cycle_audio_devices')
    def test_multiple_devices_cycles(self, mock_cycle):
        """Should cycle when multiple devices configured."""
        mock_cycle.return_value = "Headphones"

        action = AudioSwitchAction({"devices": ["Speakers", "Headphones"], "type": "output"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        action.execute(event)

        mock_cycle.assert_called_once_with(["Speakers", "Headphones"], "output")

    def test_default_type_is_output(self):
        """Should default to output device type."""
        action = AudioSwitchAction({"devices": ["Speakers"]})

        assert action._device_type == "output"

    def test_respects_input_type(self):
        """Should respect input device type."""
        action = AudioSwitchAction({"devices": ["Microphone"], "type": "input"})

        assert action._device_type == "input"


class TestAudioListAction:
    """Test AudioListAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = AudioListAction({})

        with patch('k2deck.actions.audio_switch.get_audio_devices') as mock:
            event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
            action.execute(event)
            assert not mock.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = AudioListAction({})

        with patch('k2deck.actions.audio_switch.get_audio_devices') as mock:
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)
            action.execute(event)
            assert not mock.called

    @patch('k2deck.actions.audio_switch.get_audio_devices')
    def test_lists_devices(self, mock_get):
        """Should list audio devices."""
        mock_get.return_value = [
            AudioDevice(id="id1", name="Speakers", is_default=True),
            AudioDevice(id="id2", name="Headphones", is_default=False),
        ]

        action = AudioListAction({"type": "output"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        # Should not raise
        action.execute(event)

        mock_get.assert_called_once_with("output")
