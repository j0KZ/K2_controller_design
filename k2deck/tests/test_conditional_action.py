"""Tests for conditional.py - Context-aware conditional actions."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from k2deck.actions.conditional import ConditionalAction
from k2deck.actions.multi import MultiToggleAction, _toggle_states
from k2deck.core.action_factory import (
    MAX_ACTION_DEPTH,
    ActionCreationError,
    create_action,
)
from k2deck.core.context import ContextCache


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""

    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestContextCache:
    """Test ContextCache class."""

    def setup_method(self):
        """Reset state before each test."""
        _toggle_states.clear()

    @patch("k2deck.core.context.win32gui")
    @patch("k2deck.core.context.win32process")
    @patch("k2deck.core.context.psutil")
    def test_get_foreground_app_returns_app_info(
        self, mock_psutil, mock_process, mock_gui
    ):
        """Should return AppInfo with correct data."""
        mock_gui.GetForegroundWindow.return_value = 12345
        mock_gui.GetWindowText.return_value = "Spotify Premium"
        mock_process.GetWindowThreadProcessId.return_value = (0, 1234)

        mock_proc = MagicMock()
        mock_proc.name.return_value = "Spotify.exe"
        mock_psutil.Process.return_value = mock_proc

        cache = ContextCache(refresh_interval=0)
        result = cache.get_foreground_app()

        assert result is not None
        assert result.name == "Spotify.exe"
        assert result.title == "Spotify Premium"
        assert result.pid == 1234
        assert result.hwnd == 12345

    @patch("k2deck.core.context.win32gui")
    @patch("k2deck.core.context.win32process")
    @patch("k2deck.core.context.psutil")
    def test_is_app_focused_case_insensitive(self, mock_psutil, mock_process, mock_gui):
        """App name matching should be case insensitive."""
        mock_gui.GetForegroundWindow.return_value = 12345
        mock_gui.GetWindowText.return_value = ""
        mock_process.GetWindowThreadProcessId.return_value = (0, 1234)

        mock_proc = MagicMock()
        mock_proc.name.return_value = "Spotify.exe"
        mock_psutil.Process.return_value = mock_proc

        cache = ContextCache(refresh_interval=0)

        assert cache.is_app_focused("spotify") is True
        assert cache.is_app_focused("SPOTIFY") is True
        assert cache.is_app_focused("Spotify.exe") is True

    @patch("k2deck.core.context.win32gui")
    @patch("k2deck.core.context.win32process")
    @patch("k2deck.core.context.psutil")
    def test_is_app_focused_partial_match(self, mock_psutil, mock_process, mock_gui):
        """Should support partial matching."""
        mock_gui.GetForegroundWindow.return_value = 12345
        mock_gui.GetWindowText.return_value = ""
        mock_process.GetWindowThreadProcessId.return_value = (0, 1234)

        mock_proc = MagicMock()
        mock_proc.name.return_value = "Spotify.exe"
        mock_psutil.Process.return_value = mock_proc

        cache = ContextCache(refresh_interval=0)

        assert cache.is_app_focused("spot") is True
        assert cache.is_app_focused("chrome") is False

    @patch("k2deck.core.context.psutil")
    def test_is_app_running(self, mock_psutil):
        """Should detect running applications."""
        # Create mock process iterator
        mock_proc1 = MagicMock()
        mock_proc1.info = {"pid": 1234, "name": "Spotify.exe"}
        mock_proc2 = MagicMock()
        mock_proc2.info = {"pid": 5678, "name": "chrome.exe"}

        mock_psutil.process_iter.return_value = [mock_proc1, mock_proc2]

        cache = ContextCache(refresh_interval=0)

        assert cache.is_app_running("Spotify") is True
        assert cache.is_app_running("chrome") is True
        assert cache.is_app_running("firefox") is False


class TestActionFactory:
    """Test action factory functions."""

    def test_create_action_with_valid_config(self):
        """Should create action from valid config."""
        config = {"action": "noop"}
        action = create_action(config)

        assert action is not None

    def test_create_action_with_invalid_action_type(self):
        """Should return None for unknown action type."""
        config = {"action": "unknown_action_type"}
        action = create_action(config)

        assert action is None

    def test_create_action_without_action_key(self):
        """Should return None if action key missing."""
        config = {"keys": ["a"]}
        action = create_action(config)

        assert action is None

    def test_create_action_depth_limit(self):
        """Should raise error if depth limit exceeded."""
        config = {"action": "noop"}

        with pytest.raises(ActionCreationError) as exc_info:
            create_action(config, depth=MAX_ACTION_DEPTH + 1)

        assert "Maximum action depth" in str(exc_info.value)


class TestConditionalAction:
    """Test ConditionalAction class."""

    def setup_method(self):
        """Reset state before each test."""
        _toggle_states.clear()

    @patch("k2deck.actions.conditional.is_app_focused")
    def test_executes_matching_condition(self, mock_focused):
        """Should execute action when condition matches."""
        mock_focused.return_value = True

        action = ConditionalAction(
            {"conditions": [{"app_focused": "Spotify.exe", "then": {"action": "noop"}}]}
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise
        action.execute(event)
        mock_focused.assert_called_with("Spotify.exe")

    @patch("k2deck.actions.conditional.is_app_focused")
    @patch("k2deck.actions.conditional.create_action")
    def test_executes_first_matching_condition(self, mock_create, mock_focused):
        """Should execute only the first matching condition."""
        # First condition matches
        mock_focused.return_value = True

        executed_actions = []
        mock_action = MagicMock()
        mock_action.execute = lambda e: executed_actions.append("executed")
        mock_create.return_value = mock_action

        action = ConditionalAction(
            {
                "_depth": 0,
                "conditions": [
                    {"app_focused": "Spotify.exe", "then": {"action": "noop"}},
                    {"app_focused": "Chrome.exe", "then": {"action": "noop"}},
                ],
            }
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        action.execute(event)

        # Only first condition's action should be created and executed
        assert len(executed_actions) == 1
        # is_app_focused should only be called once (first match stops)
        mock_focused.assert_called_once_with("Spotify.exe")

    @patch("k2deck.actions.conditional.is_app_focused")
    def test_executes_default_when_no_match(self, mock_focused):
        """Should execute default action when no conditions match."""
        mock_focused.return_value = False

        action = ConditionalAction(
            {
                "conditions": [
                    {"app_focused": "Spotify.exe", "then": {"action": "noop"}}
                ],
                "default": {"action": "noop"},
            }
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise
        action.execute(event)

    @patch("k2deck.actions.conditional.is_app_focused")
    def test_no_action_when_no_match_and_no_default(self, mock_focused):
        """Should do nothing when no conditions match and no default."""
        mock_focused.return_value = False

        action = ConditionalAction(
            {"conditions": [{"app_focused": "Spotify.exe", "then": {"action": "noop"}}]}
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise
        action.execute(event)

    @patch("k2deck.actions.conditional.is_app_running")
    def test_app_running_condition(self, mock_running):
        """Should check if app is running."""
        mock_running.return_value = True

        action = ConditionalAction(
            {"conditions": [{"app_running": "Spotify.exe", "then": {"action": "noop"}}]}
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        action.execute(event)

        mock_running.assert_called_with("Spotify.exe")

    def test_toggle_state_condition_true(self):
        """Should check toggle state condition (true)."""
        # Set toggle state
        MultiToggleAction.set_state(42, True)

        action = ConditionalAction(
            {
                "conditions": [
                    {
                        "toggle_state": {"note": 42, "state": True},
                        "then": {"action": "noop"},
                    }
                ]
            }
        )

        # Should match since toggle 42 is True
        result = action._check_condition({"toggle_state": {"note": 42, "state": True}})
        assert result is True

    def test_toggle_state_condition_false(self):
        """Should check toggle state condition (false)."""
        # Toggle 42 is False by default
        _toggle_states.clear()

        action = ConditionalAction(
            {
                "conditions": [
                    {
                        "toggle_state": {"note": 42, "state": False},
                        "then": {"action": "noop"},
                    }
                ]
            }
        )

        # Should match since toggle 42 is False
        result = action._check_condition({"toggle_state": {"note": 42, "state": False}})
        assert result is True

    def test_toggle_state_condition_mismatch(self):
        """Should not match when toggle state doesn't match."""
        MultiToggleAction.set_state(42, True)

        action = ConditionalAction({"conditions": []})

        # Expecting False but it's True
        result = action._check_condition({"toggle_state": {"note": 42, "state": False}})
        assert result is False

    @patch("k2deck.actions.conditional.is_app_focused")
    @patch("k2deck.actions.conditional.is_app_running")
    def test_multiple_conditions_all_must_match(self, mock_running, mock_focused):
        """All conditions in a single entry must match."""
        mock_focused.return_value = True
        mock_running.return_value = False

        action = ConditionalAction({"conditions": []})

        # app_focused matches but app_running doesn't
        result = action._check_condition(
            {"app_focused": "Spotify.exe", "app_running": "OBS.exe"}
        )
        assert result is False

        # Both match
        mock_running.return_value = True
        result = action._check_condition(
            {"app_focused": "Spotify.exe", "app_running": "OBS.exe"}
        )
        assert result is True

    def test_empty_condition_always_matches(self):
        """Empty condition should always match."""
        action = ConditionalAction({"conditions": []})

        result = action._check_condition({})
        assert result is True

    def test_depth_limit_prevents_execution(self):
        """Should not execute if at max depth."""
        action = ConditionalAction(
            {"_depth": MAX_ACTION_DEPTH, "conditions": [{"then": {"action": "noop"}}]}
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise, just skip
        action.execute(event)


class TestConditionalActionIntegration:
    """Integration tests for conditional action with real nested actions."""

    def setup_method(self):
        """Reset state before each test."""
        _toggle_states.clear()

    @patch("k2deck.actions.conditional.is_app_focused")
    @patch("k2deck.core.keyboard.execute_hotkey")
    def test_executes_hotkey_action(self, mock_hotkey, mock_focused):
        """Should execute nested hotkey action."""
        mock_focused.return_value = True

        action = ConditionalAction(
            {
                "conditions": [
                    {
                        "app_focused": "vlc.exe",
                        "then": {"action": "hotkey", "keys": ["space"]},
                    }
                ]
            }
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        action.execute(event)

        mock_hotkey.assert_called_once()
        call_args = mock_hotkey.call_args[0][0]
        assert call_args == ["space"]

    @patch("k2deck.actions.conditional.is_app_focused")
    def test_nested_conditional_respects_depth(self, mock_focused):
        """Nested conditional should increment depth."""
        mock_focused.return_value = True

        # Create deeply nested conditional
        action = ConditionalAction(
            {
                "_depth": 0,
                "conditions": [
                    {
                        "app_focused": "test.exe",
                        "then": {
                            "action": "conditional",
                            "conditions": [
                                {"app_focused": "test.exe", "then": {"action": "noop"}}
                            ],
                        },
                    }
                ],
            }
        )

        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise
        action.execute(event)
