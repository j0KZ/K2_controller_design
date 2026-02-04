"""Tests for folder.py and folders.py - Folder navigation and actions."""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from k2deck.core.folders import FolderManager, get_folder_manager, MAX_DEPTH
from k2deck.actions.folder import FolderAction, FolderBackAction, FolderRootAction


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""
    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestFolderManager:
    """Test FolderManager class."""

    def setup_method(self):
        """Reset singleton for each test."""
        FolderManager._instance = None

    def test_singleton_pattern(self):
        """Should return same instance."""
        mgr1 = FolderManager()
        mgr2 = FolderManager()
        assert mgr1 is mgr2

    def test_get_folder_manager_returns_singleton(self):
        """get_folder_manager should return singleton."""
        mgr1 = get_folder_manager()
        mgr2 = get_folder_manager()
        assert mgr1 is mgr2

    def test_initial_state_is_root(self):
        """Should start at root (no folder)."""
        mgr = FolderManager()
        assert mgr.current_folder is None
        assert mgr.in_folder is False
        assert mgr.depth == 0

    def test_enter_folder(self):
        """Should enter folder."""
        mgr = FolderManager()
        result = mgr.enter_folder("test_folder")
        assert result is True
        assert mgr.current_folder == "test_folder"
        assert mgr.in_folder is True
        assert mgr.depth == 1

    def test_enter_empty_folder_fails(self):
        """Should not enter empty folder name."""
        mgr = FolderManager()
        result = mgr.enter_folder("")
        assert result is False
        assert mgr.in_folder is False

    def test_exit_folder_to_root(self):
        """Should exit folder to root."""
        mgr = FolderManager()
        mgr.enter_folder("folder1")
        mgr.exit_folder()
        assert mgr.current_folder is None
        assert mgr.in_folder is False

    def test_nested_folders(self):
        """Should handle nested folders."""
        mgr = FolderManager()
        mgr.enter_folder("level1")
        mgr.enter_folder("level2")
        assert mgr.current_folder == "level2"
        assert mgr.depth == 2

        mgr.exit_folder()
        assert mgr.current_folder == "level1"
        assert mgr.depth == 1

        mgr.exit_folder()
        assert mgr.current_folder is None
        assert mgr.depth == 0

    def test_max_depth_enforced(self):
        """Should enforce max depth."""
        mgr = FolderManager()
        # Enter up to max depth
        for i in range(MAX_DEPTH):
            result = mgr.enter_folder(f"level{i+1}")
            assert result is True

        # Trying to exceed max depth should fail
        result = mgr.enter_folder("too_deep")
        assert result is False
        assert mgr.depth == MAX_DEPTH

    def test_exit_to_root(self):
        """Should exit all folders to root."""
        mgr = FolderManager()
        mgr.enter_folder("level1")
        mgr.enter_folder("level2")
        mgr.enter_folder("level3")

        mgr.exit_to_root()
        assert mgr.current_folder is None
        assert mgr.in_folder is False
        assert mgr.depth == 0

    def test_callback_on_enter(self):
        """Should call callback when entering folder."""
        mgr = FolderManager()
        callback = MagicMock()
        mgr.register_callback(callback)

        mgr.enter_folder("test")
        callback.assert_called_once_with("test")

    def test_callback_on_exit(self):
        """Should call callback when exiting folder."""
        mgr = FolderManager()
        callback = MagicMock()
        mgr.enter_folder("test")

        mgr.register_callback(callback)
        mgr.exit_folder()
        callback.assert_called_once_with(None)

    def test_callback_on_exit_to_root(self):
        """Should call callback when exiting to root."""
        mgr = FolderManager()
        callback = MagicMock()
        mgr.enter_folder("level1")
        mgr.enter_folder("level2")

        mgr.register_callback(callback)
        mgr.exit_to_root()
        callback.assert_called_once_with(None)

    def test_unregister_callback(self):
        """Should unregister callback."""
        mgr = FolderManager()
        callback = MagicMock()
        mgr.register_callback(callback)
        mgr.unregister_callback(callback)

        mgr.enter_folder("test")
        callback.assert_not_called()

    def test_callback_not_registered_twice(self):
        """Should not register same callback twice."""
        mgr = FolderManager()
        callback = MagicMock()
        mgr.register_callback(callback)
        mgr.register_callback(callback)

        mgr.enter_folder("test")
        # Should only be called once
        assert callback.call_count == 1

    def test_callback_error_does_not_break_others(self):
        """Callback error should not prevent other callbacks."""
        mgr = FolderManager()
        bad_callback = MagicMock(side_effect=Exception("Error"))
        good_callback = MagicMock()

        mgr.register_callback(bad_callback)
        mgr.register_callback(good_callback)

        # Should not raise
        mgr.enter_folder("test")
        good_callback.assert_called_once_with("test")


class TestFolderAction:
    """Test FolderAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        FolderManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = FolderAction({"folder": "test"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
        action.execute(event)
        assert get_folder_manager().in_folder is False

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = FolderAction({"folder": "test"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)
        action.execute(event)
        assert get_folder_manager().in_folder is False

    def test_enters_folder(self):
        """Should enter configured folder."""
        action = FolderAction({"folder": "my_folder"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
        action.execute(event)
        assert get_folder_manager().current_folder == "my_folder"

    def test_no_folder_configured(self):
        """Should warn if no folder configured."""
        action = FolderAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
        action.execute(event)
        assert get_folder_manager().in_folder is False


class TestFolderBackAction:
    """Test FolderBackAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        FolderManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        get_folder_manager().enter_folder("test")
        action = FolderBackAction({})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
        action.execute(event)
        assert get_folder_manager().in_folder is True  # Should still be in folder

    def test_exits_folder(self):
        """Should exit current folder."""
        get_folder_manager().enter_folder("test")
        action = FolderBackAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
        action.execute(event)
        assert get_folder_manager().in_folder is False


class TestFolderRootAction:
    """Test FolderRootAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        FolderManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        mgr = get_folder_manager()
        mgr.enter_folder("level1")
        mgr.enter_folder("level2")

        action = FolderRootAction({})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
        action.execute(event)
        assert mgr.in_folder is True  # Should still be in folder

    def test_exits_to_root(self):
        """Should exit all folders to root."""
        mgr = get_folder_manager()
        mgr.enter_folder("level1")
        mgr.enter_folder("level2")

        action = FolderRootAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
        action.execute(event)
        assert mgr.in_folder is False
        assert mgr.depth == 0
