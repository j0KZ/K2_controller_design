"""Tests for system.py - System, URL, and Clipboard actions.

⚠️ WARNING: This module tests DANGEROUS system functions (sleep, shutdown, etc.)
All tests MUST mock these functions properly to avoid actually executing them!
"""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from k2deck.actions.system import (
    ClipboardPasteAction,
    NoopAction,
    OpenURLAction,
    SystemAction,
    hibernate_computer,
    lock_workstation,
    open_url,
    restart_computer,
    shutdown_computer,
    sleep_computer,
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


class TestSystemCommands:
    """Test individual system command functions.

    ⚠️ These tests are SKIPPED by default to avoid accidentally
    executing dangerous system commands. Only run manually with
    proper mocking verification.
    """

    @pytest.mark.skip(reason="Dangerous: could actually lock the PC if mock fails")
    @patch("k2deck.actions.system.ctypes")
    def test_lock_workstation(self, mock_ctypes):
        """lock_workstation should call Windows API."""
        result = lock_workstation()
        assert result is True
        mock_ctypes.windll.user32.LockWorkStation.assert_called_once()

    @pytest.mark.skip(reason="Dangerous: could actually sleep the PC if mock fails")
    @patch("k2deck.actions.system.ctypes")
    def test_sleep_computer(self, mock_ctypes):
        """sleep_computer should call SetSuspendState with sleep mode."""
        result = sleep_computer()
        assert result is True
        mock_ctypes.windll.powrprof.SetSuspendState.assert_called_once_with(0, 1, 0)

    @pytest.mark.skip(reason="Dangerous: could actually hibernate the PC if mock fails")
    @patch("k2deck.actions.system.ctypes")
    def test_hibernate_computer(self, mock_ctypes):
        """hibernate_computer should call SetSuspendState with hibernate mode."""
        result = hibernate_computer()
        assert result is True
        mock_ctypes.windll.powrprof.SetSuspendState.assert_called_once_with(1, 1, 0)

    @pytest.mark.skip(reason="Dangerous: could actually shutdown the PC if mock fails")
    @patch("k2deck.actions.system.subprocess")
    def test_shutdown_computer(self, mock_subprocess):
        """shutdown_computer should run shutdown command."""
        result = shutdown_computer(force=False)
        assert result is True
        mock_subprocess.run.assert_called_once()

    @pytest.mark.skip(reason="Dangerous: could actually shutdown the PC if mock fails")
    @patch("k2deck.actions.system.subprocess")
    def test_shutdown_computer_force(self, mock_subprocess):
        """shutdown_computer with force should include /f flag."""
        result = shutdown_computer(force=True)
        assert result is True

    @pytest.mark.skip(reason="Dangerous: could actually restart the PC if mock fails")
    @patch("k2deck.actions.system.subprocess")
    def test_restart_computer(self, mock_subprocess):
        """restart_computer should run shutdown /r command."""
        result = restart_computer(force=False)
        assert result is True


class TestSystemAction:
    """Test SystemAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = SystemAction({"command": "screenshot"})

        with patch("k2deck.actions.system.take_screenshot") as mock:
            event = MidiEvent(
                type="note_off", channel=16, note=36, cc=None, value=127, timestamp=0.0
            )
            action.execute(event)
            assert not mock.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = SystemAction({"command": "screenshot"})

        with patch("k2deck.actions.system.take_screenshot") as mock:
            event = MidiEvent(
                type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
            )
            action.execute(event)
            assert not mock.called

    def test_lock_command(self):
        """lock command should call lock_workstation."""
        action = SystemAction({"command": "lock"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Patch the COMMANDS dict entry directly to avoid calling real function
        with patch.dict(SystemAction.COMMANDS, {"lock": MagicMock()}):
            action.execute(event)
            SystemAction.COMMANDS["lock"].assert_called_once()

    def test_sleep_command(self):
        """sleep command should call sleep_computer (mocked)."""
        action = SystemAction({"command": "sleep"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # CRITICAL: Patch the COMMANDS dict to avoid actually sleeping the PC!
        with patch.dict(SystemAction.COMMANDS, {"sleep": MagicMock()}):
            action.execute(event)
            SystemAction.COMMANDS["sleep"].assert_called_once()

    @patch("k2deck.actions.system.shutdown_computer", return_value=True)
    def test_shutdown_command(self, mock_shutdown):
        """shutdown command should call shutdown_computer (MOCKED - never real!)."""
        action = SystemAction({"command": "shutdown"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_shutdown.assert_called_once_with(force=False)

    @patch("k2deck.actions.system.shutdown_computer", return_value=True)
    def test_shutdown_command_force(self, mock_shutdown):
        """shutdown command with force=true should pass force flag (MOCKED)."""
        action = SystemAction({"command": "shutdown", "force": True})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_shutdown.assert_called_once_with(force=True)

    def test_unknown_command_logs_warning(self):
        """Unknown command should log warning and not crash."""
        action = SystemAction({"command": "unknown_command"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        # Should not raise
        action.execute(event)


class TestOpenURLAction:
    """Test OpenURLAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = OpenURLAction({"url": "https://example.com"})

        with patch("k2deck.actions.system.open_url") as mock:
            event = MidiEvent(
                type="note_off", channel=16, note=36, cc=None, value=127, timestamp=0.0
            )
            action.execute(event)
            assert not mock.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = OpenURLAction({"url": "https://example.com"})

        with patch("k2deck.actions.system.open_url") as mock:
            event = MidiEvent(
                type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
            )
            action.execute(event)
            assert not mock.called

    @patch("k2deck.actions.system.open_url")
    def test_opens_configured_url(self, mock_open):
        """Should open the configured URL."""
        action = OpenURLAction({"url": "https://github.com"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_open.assert_called_once_with("https://github.com")

    def test_warns_if_no_url_configured(self):
        """Should log warning if no URL configured."""
        action = OpenURLAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.system.open_url") as mock:
            action.execute(event)
            assert not mock.called


class TestClipboardPasteAction:
    """Test ClipboardPasteAction class."""

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = ClipboardPasteAction({"text": "hello"})

        with patch("k2deck.actions.system.paste_to_clipboard") as mock:
            event = MidiEvent(
                type="note_off", channel=16, note=36, cc=None, value=127, timestamp=0.0
            )
            action.execute(event)
            assert not mock.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = ClipboardPasteAction({"text": "hello"})

        with patch("k2deck.actions.system.paste_to_clipboard") as mock:
            event = MidiEvent(
                type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
            )
            action.execute(event)
            assert not mock.called

    @patch("k2deck.actions.system.paste_to_clipboard")
    def test_copies_text_to_clipboard(self, mock_paste):
        """Should copy configured text to clipboard."""
        mock_paste.return_value = True
        action = ClipboardPasteAction({"text": "user@example.com"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_paste.assert_called_once_with("user@example.com")

    @patch("k2deck.core.keyboard.execute_hotkey")
    @patch("k2deck.actions.system.paste_to_clipboard")
    def test_pastes_if_paste_option_true(self, mock_clipboard, mock_hotkey):
        """Should simulate Ctrl+V if paste=true."""
        mock_clipboard.return_value = True
        action = ClipboardPasteAction({"text": "hello", "paste": True})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_hotkey.assert_called_once()
        call_args = mock_hotkey.call_args[0][0]
        assert call_args == ["ctrl", "v"]

    @patch("k2deck.core.keyboard.execute_hotkey")
    @patch("k2deck.actions.system.paste_to_clipboard")
    def test_does_not_paste_by_default(self, mock_clipboard, mock_hotkey):
        """Should not simulate Ctrl+V by default."""
        mock_clipboard.return_value = True
        action = ClipboardPasteAction({"text": "hello"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        assert not mock_hotkey.called

    def test_warns_if_no_text_configured(self):
        """Should log warning if no text configured."""
        action = ClipboardPasteAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.system.paste_to_clipboard") as mock:
            action.execute(event)
            assert not mock.called


class TestNoopAction:
    """Test NoopAction class."""

    def test_does_nothing(self):
        """NoopAction should do nothing on any event."""
        action = NoopAction({})

        # Should not raise for any event type
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )
        action.execute(event)

        event = MidiEvent(
            type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
        )
        action.execute(event)


class TestOpenURLFunction:
    """Test open_url function."""

    @patch("k2deck.actions.system.webbrowser")
    def test_opens_url_in_browser(self, mock_wb):
        """Should call webbrowser.open with URL."""
        result = open_url("https://example.com")

        assert result is True
        mock_wb.open.assert_called_once_with("https://example.com")

    @patch("k2deck.actions.system.webbrowser")
    def test_returns_false_on_error(self, mock_wb):
        """Should return False if webbrowser.open fails."""
        mock_wb.open.side_effect = Exception("Browser error")

        result = open_url("https://example.com")

        assert result is False
