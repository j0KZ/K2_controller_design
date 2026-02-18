"""Tests for multi.py - Multi-action and MultiToggle actions."""

from dataclasses import dataclass
from unittest.mock import patch

from k2deck.actions.multi import (
    MultiAction,
    MultiToggleAction,
    _last_toggle_time,
    _toggle_states,
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


class TestMultiAction:
    """Test MultiAction class."""

    def setup_method(self):
        """Reset state before each test."""
        _toggle_states.clear()
        _last_toggle_time.clear()

    @patch("k2deck.actions.multi.keyboard")
    def test_only_triggers_on_note_on(self, mock_kb):
        """Should only execute on note_on events."""
        action = MultiAction({"sequence": [["a"]]})

        # note_off should do nothing
        event = MidiEvent(
            type="note_off", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        action.execute(event)
        assert not mock_kb.execute_hotkey.called

        # cc should do nothing
        event = MidiEvent(
            type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
        )
        action.execute(event)
        assert not mock_kb.execute_hotkey.called

    @patch("k2deck.actions.multi.keyboard")
    def test_ignores_zero_velocity(self, mock_kb):
        """Should ignore note_on with velocity 0 (acts as note_off)."""
        action = MultiAction({"sequence": [["a"]]})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
        )

        action.execute(event)

        assert not mock_kb.execute_hotkey.called

    @patch("k2deck.actions.multi.keyboard")
    @patch("k2deck.actions.multi.time.sleep")
    def test_executes_sequence_in_order(self, mock_sleep, mock_kb):
        """Should execute all keys in sequence."""
        action = MultiAction(
            {
                "name": "test",
                "sequence": [["ctrl", "a"], ["ctrl", "c"], ["ctrl", "v"]],
                "delay_ms": 100,
            }
        )
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        # Check execute_hotkey was called for each sequence
        assert mock_kb.execute_hotkey.call_count == 3
        calls = [c[0][0] for c in mock_kb.execute_hotkey.call_args_list]
        assert calls == [["ctrl", "a"], ["ctrl", "c"], ["ctrl", "v"]]

    @patch("k2deck.actions.multi.keyboard")
    @patch("k2deck.actions.multi.time.sleep")
    def test_releases_modifiers_before_and_after(self, mock_sleep, mock_kb):
        """Should call release_all_modifiers at start and end."""
        action = MultiAction({"sequence": [["ctrl", "a"]], "delay_ms": 10})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        # Should be called at least twice (before and after)
        assert mock_kb.release_all_modifiers.call_count >= 2


class TestMultiToggleAction:
    """Test MultiToggleAction class."""

    def setup_method(self):
        """Reset state before each test."""
        _toggle_states.clear()
        _last_toggle_time.clear()

    @patch("k2deck.actions.multi.keyboard")
    def test_only_triggers_on_note_on(self, mock_kb):
        """Should only execute on note_on events."""
        action = MultiToggleAction({"on_sequence": [["a"]], "off_sequence": [["b"]]})

        event = MidiEvent(
            type="note_off", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        action.execute(event)
        assert not mock_kb.execute_hotkey.called

    @patch("k2deck.actions.multi.keyboard")
    def test_ignores_zero_velocity(self, mock_kb):
        """Should ignore note_on with velocity 0."""
        action = MultiToggleAction({"on_sequence": [["a"]], "off_sequence": [["b"]]})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
        )

        action.execute(event)

        assert not mock_kb.execute_hotkey.called

    @patch("k2deck.actions.multi.keyboard")
    @patch("k2deck.actions.multi.time.sleep")
    def test_first_press_executes_on_sequence(self, mock_sleep, mock_kb):
        """First press should execute on_sequence (starting state is OFF)."""
        action = MultiToggleAction(
            {
                "name": "test",
                "on_sequence": [["ctrl", "m"]],
                "off_sequence": [["ctrl", "u"]],
                "delay_ms": 10,
            }
        )
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        # Should execute on_sequence
        mock_kb.execute_hotkey.assert_called_once()
        assert mock_kb.execute_hotkey.call_args[0][0] == ["ctrl", "m"]
        # State should be ON now
        assert _toggle_states.get(36) is True

    @patch("k2deck.actions.multi.keyboard")
    @patch("k2deck.actions.multi.time.sleep")
    def test_second_press_executes_off_sequence(self, mock_sleep, mock_kb):
        """Second press should execute off_sequence."""
        action = MultiToggleAction(
            {
                "name": "test",
                "on_sequence": [["ctrl", "m"]],
                "off_sequence": [["ctrl", "u"]],
                "delay_ms": 10,
            }
        )
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # First press - sets state to ON
        action.execute(event)
        mock_kb.reset_mock()

        # Wait to avoid debounce
        _last_toggle_time[36] = 0

        # Second press - should execute off_sequence
        action.execute(event)

        mock_kb.execute_hotkey.assert_called_once()
        assert mock_kb.execute_hotkey.call_args[0][0] == ["ctrl", "u"]
        # State should be OFF now
        assert _toggle_states.get(36) is False

    @patch("k2deck.actions.multi.keyboard")
    def test_debounce_prevents_rapid_toggles(self, mock_kb):
        """Rapid presses should be debounced."""
        action = MultiToggleAction(
            {"on_sequence": [["a"]], "off_sequence": [["b"]], "delay_ms": 1}
        )
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # First press
        action.execute(event)
        call_count_after_first = mock_kb.execute_hotkey.call_count

        # Immediate second press (should be debounced)
        action.execute(event)
        call_count_after_second = mock_kb.execute_hotkey.call_count

        # Should not have executed again
        assert call_count_after_second == call_count_after_first

    def test_get_state(self):
        """get_state should return current toggle state."""
        _toggle_states[36] = True
        _toggle_states[37] = False

        assert MultiToggleAction.get_state(36) is True
        assert MultiToggleAction.get_state(37) is False
        assert MultiToggleAction.get_state(99) is False  # Default

    def test_set_state(self):
        """set_state should manually set toggle state."""
        MultiToggleAction.set_state(36, True)
        assert _toggle_states[36] is True

        MultiToggleAction.set_state(36, False)
        assert _toggle_states[36] is False

    def test_reset_all(self):
        """reset_all should clear all toggle states."""
        _toggle_states[36] = True
        _toggle_states[37] = False
        _toggle_states[38] = True

        MultiToggleAction.reset_all()

        assert len(_toggle_states) == 0

    @patch("k2deck.actions.multi.keyboard")
    @patch("k2deck.actions.multi.time.sleep")
    def test_different_notes_have_independent_state(self, mock_sleep, mock_kb):
        """Each note should have its own toggle state."""
        action1 = MultiToggleAction(
            {"on_sequence": [["a"]], "off_sequence": [["b"]], "delay_ms": 1}
        )
        action2 = MultiToggleAction(
            {"on_sequence": [["c"]], "off_sequence": [["d"]], "delay_ms": 1}
        )

        event36 = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        event37 = MidiEvent(
            type="note_on", channel=16, note=37, cc=None, value=127, timestamp=0.0
        )

        # Press note 36
        action1.execute(event36)
        assert _toggle_states.get(36) is True
        assert _toggle_states.get(37, False) is False

        # Press note 37
        action2.execute(event37)
        assert _toggle_states.get(36) is True
        assert _toggle_states.get(37) is True

    @patch("k2deck.actions.multi.keyboard")
    @patch("k2deck.actions.multi.time.sleep")
    def test_executes_full_sequence(self, mock_sleep, mock_kb):
        """Should execute all steps in on/off sequence."""
        action = MultiToggleAction(
            {
                "name": "test",
                "on_sequence": [["ctrl", "m"], ["ctrl", "space"]],
                "off_sequence": [["ctrl", "space"], ["ctrl", "m"]],
                "delay_ms": 10,
            }
        )
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        # Should execute both steps of on_sequence
        assert mock_kb.execute_hotkey.call_count == 2
        calls = [c[0][0] for c in mock_kb.execute_hotkey.call_args_list]
        assert calls == [["ctrl", "m"], ["ctrl", "space"]]
