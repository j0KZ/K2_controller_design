"""Tests for hotkey action."""

from unittest.mock import MagicMock, patch

import pytest
from pynput.keyboard import Key

from k2deck.actions.hotkey import (
    HotkeyAction,
    HotkeyRelativeAction,
    parse_key,
)
from k2deck.core.midi_listener import MidiEvent


class TestParseKey:
    """Tests for key parsing."""

    def test_parse_modifier_keys(self):
        """Should parse modifier keys."""
        assert parse_key("ctrl") == Key.ctrl
        assert parse_key("alt") == Key.alt
        assert parse_key("shift") == Key.shift
        assert parse_key("win") == Key.cmd

    def test_parse_function_keys(self):
        """Should parse function keys."""
        assert parse_key("f1") == Key.f1
        assert parse_key("f5") == Key.f5
        assert parse_key("f12") == Key.f12

    def test_parse_special_keys(self):
        """Should parse special keys."""
        assert parse_key("space") == Key.space
        assert parse_key("enter") == Key.enter
        assert parse_key("tab") == Key.tab
        assert parse_key("escape") == Key.esc

    def test_parse_media_keys(self):
        """Should parse media keys."""
        assert parse_key("media_play_pause") == Key.media_play_pause
        assert parse_key("media_next") == Key.media_next
        assert parse_key("volume_mute") == Key.media_volume_mute

    def test_parse_single_char(self):
        """Should parse single characters."""
        key = parse_key("a")
        assert key.char == "a"

    def test_parse_case_insensitive(self):
        """Should be case insensitive for special keys."""
        assert parse_key("CTRL") == Key.ctrl
        assert parse_key("Shift") == Key.shift


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
