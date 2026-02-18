"""Tests for hotkey action."""

from unittest.mock import patch

from k2deck.actions.hotkey import (
    HotkeyAction,
    HotkeyRelativeAction,
)
from k2deck.core.midi_listener import MidiEvent


class TestHotkeyAction:
    """Tests for HotkeyAction."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on Note On with velocity > 0."""
        config = {"name": "Test", "action": "hotkey", "keys": ["a"]}
        action = HotkeyAction(config)

        with patch("k2deck.actions.hotkey.execute_hotkey") as mock:
            # Note On with velocity
            event = MidiEvent(
                type="note_on",
                channel=16,
                note=36,
                cc=None,
                value=127,
                timestamp=0.0,
            )
            action.execute(event)
            mock.assert_called_once_with(["a"])

    def test_ignores_note_off(self):
        """Should ignore Note Off events."""
        config = {"name": "Test", "action": "hotkey", "keys": ["a"]}
        action = HotkeyAction(config)

        with patch("k2deck.actions.hotkey.execute_hotkey") as mock:
            event = MidiEvent(
                type="note_off",
                channel=16,
                note=36,
                cc=None,
                value=0,
                timestamp=0.0,
            )
            action.execute(event)
            mock.assert_not_called()

    def test_ignores_zero_velocity(self):
        """Should ignore Note On with velocity 0 (treated as Note Off)."""
        config = {"name": "Test", "action": "hotkey", "keys": ["a"]}
        action = HotkeyAction(config)

        with patch("k2deck.actions.hotkey.execute_hotkey") as mock:
            event = MidiEvent(
                type="note_on",
                channel=16,
                note=36,
                cc=None,
                value=0,
                timestamp=0.0,
            )
            action.execute(event)
            mock.assert_not_called()

    def test_hold_mode_press_and_release(self):
        """Should hold keys in hold mode and release on button release."""
        config = {"name": "Test", "action": "hotkey", "keys": ["v"], "mode": "hold"}
        action = HotkeyAction(config)

        with (
            patch("k2deck.core.keyboard.press_key") as mock_press,
            patch("k2deck.core.keyboard.release_key") as mock_release,
        ):
            # Button press
            press_event = MidiEvent(
                type="note_on",
                channel=16,
                note=36,
                cc=None,
                value=127,
                timestamp=0.0,
            )
            action.execute(press_event)
            mock_press.assert_called_once_with("v")

            # Button release (note_on with velocity 0)
            release_event = MidiEvent(
                type="note_on",
                channel=16,
                note=36,
                cc=None,
                value=0,
                timestamp=0.1,
            )
            action.execute(release_event)
            mock_release.assert_called_once_with("v")


class TestHotkeyRelativeAction:
    """Tests for HotkeyRelativeAction."""

    def test_cw_triggers_cw_keys(self):
        """Should execute CW keys on clockwise turn."""
        config = {
            "name": "Test",
            "action": "hotkey_relative",
            "cw": ["ctrl", "tab"],
            "ccw": ["ctrl", "shift", "tab"],
        }
        action = HotkeyRelativeAction(config)

        with patch("k2deck.actions.hotkey.execute_hotkey") as mock:
            event = MidiEvent(
                type="cc",
                channel=16,
                note=None,
                cc=16,
                value=1,  # CW
                timestamp=0.0,
            )
            action.execute(event)
            mock.assert_called_once_with(["ctrl", "tab"])

    def test_ccw_triggers_ccw_keys(self):
        """Should execute CCW keys on counter-clockwise turn."""
        config = {
            "name": "Test",
            "action": "hotkey_relative",
            "cw": ["ctrl", "tab"],
            "ccw": ["ctrl", "shift", "tab"],
        }
        action = HotkeyRelativeAction(config)

        with patch("k2deck.actions.hotkey.execute_hotkey") as mock:
            event = MidiEvent(
                type="cc",
                channel=16,
                note=None,
                cc=16,
                value=127,  # CCW
                timestamp=0.0,
            )
            action.execute(event)
            mock.assert_called_once_with(["ctrl", "shift", "tab"])

    def test_ignores_non_cc_events(self):
        """Should ignore non-CC events."""
        config = {
            "name": "Test",
            "action": "hotkey_relative",
            "cw": ["a"],
            "ccw": ["b"],
        }
        action = HotkeyRelativeAction(config)

        with patch("k2deck.actions.hotkey.execute_hotkey") as mock:
            event = MidiEvent(
                type="note_on",
                channel=16,
                note=36,
                cc=None,
                value=127,
                timestamp=0.0,
            )
            action.execute(event)
            mock.assert_not_called()
