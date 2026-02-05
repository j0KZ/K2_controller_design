"""Tests for AnalogStateManager - fader/pot position persistence."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from k2deck.core.analog_state import AnalogStateManager, get_analog_state_manager


class TestAnalogStateManager:
    """Test AnalogStateManager class."""

    def setup_method(self, tmp_path_factory):
        """Reset singleton before each test with isolated state file."""
        AnalogStateManager._instance = None
        # Create fresh manager with temp state file to avoid disk pollution
        self.tmp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.tmp_dir) / "test_analog_state.json"

    def teardown_method(self):
        """Clean up temp files."""
        import shutil
        if hasattr(self, 'tmp_dir') and Path(self.tmp_dir).exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        AnalogStateManager._instance = None

    def _get_fresh_manager(self) -> AnalogStateManager:
        """Get a fresh manager with isolated state file."""
        AnalogStateManager._instance = None
        manager = AnalogStateManager()
        manager.configure(self.state_file)
        manager._positions = {}  # Clear any loaded state
        manager._callbacks = []  # Clear any callbacks
        return manager

    def test_singleton_pattern(self):
        """Should return same instance."""
        manager1 = self._get_fresh_manager()
        manager2 = AnalogStateManager()
        assert manager1 is manager2

    def test_get_analog_state_manager(self):
        """Should return singleton via helper function."""
        self._get_fresh_manager()
        manager1 = get_analog_state_manager()
        manager2 = get_analog_state_manager()
        assert manager1 is manager2

    def test_update_and_get(self):
        """Should store and retrieve values."""
        manager = self._get_fresh_manager()

        manager.update(16, 64)
        assert manager.get(16) == 64

        manager.update(17, 127)
        assert manager.get(17) == 127

    def test_get_default_value(self):
        """Should return 0 for unknown CCs."""
        manager = self._get_fresh_manager()
        assert manager.get(99) == 0

    def test_get_all(self):
        """Should return all positions."""
        manager = self._get_fresh_manager()

        manager.update(16, 50)
        manager.update(17, 100)

        positions = manager.get_all()
        assert positions == {16: 50, 17: 100}

    def test_get_all_returns_copy(self):
        """Should return a copy, not the original dict."""
        manager = self._get_fresh_manager()
        manager.update(16, 50)

        positions = manager.get_all()
        positions[16] = 999  # Modify the copy

        assert manager.get(16) == 50  # Original unchanged

    def test_update_ignores_same_value(self):
        """Should not trigger callback for same value."""
        manager = self._get_fresh_manager()
        callback = MagicMock()
        manager.register_callback(callback)

        manager.update(16, 64)
        assert callback.call_count == 1

        manager.update(16, 64)  # Same value
        assert callback.call_count == 1  # No new call

    def test_update_validates_range(self):
        """Should reject out-of-range values."""
        manager = self._get_fresh_manager()

        manager.update(16, -1)
        assert manager.get(16) == 0  # Not updated

        manager.update(16, 128)
        assert manager.get(16) == 0  # Not updated

        manager.update(16, 127)  # Valid
        assert manager.get(16) == 127

    def test_callback_registration(self):
        """Should call registered callbacks on update."""
        manager = self._get_fresh_manager()
        callback = MagicMock()

        manager.register_callback(callback)
        manager.update(16, 64)

        callback.assert_called_once_with(16, 64)

    def test_callback_unregistration(self):
        """Should not call unregistered callbacks."""
        manager = self._get_fresh_manager()
        callback = MagicMock()

        manager.register_callback(callback)
        manager.unregister_callback(callback)
        manager.update(16, 64)

        callback.assert_not_called()

    def test_callback_error_doesnt_break_others(self):
        """Should continue with other callbacks if one fails."""
        manager = self._get_fresh_manager()

        bad_callback = MagicMock(side_effect=Exception("Test error"))
        good_callback = MagicMock()

        manager.register_callback(bad_callback)
        manager.register_callback(good_callback)

        manager.update(16, 64)

        bad_callback.assert_called_once()
        good_callback.assert_called_once()

    def test_reset_clears_positions(self):
        """Should clear all positions on reset."""
        manager = self._get_fresh_manager()

        manager.update(16, 64)
        manager.update(17, 127)
        manager.reset()

        assert manager.get_all() == {}

    def test_persistence_save_and_load(self):
        """Should persist positions to file and load them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "analog_state.json"

            # Create manager and save
            AnalogStateManager._instance = None
            manager = AnalogStateManager()
            manager.configure(state_file)
            manager.update(16, 50)
            manager.update(17, 100)

            # Force immediate save
            manager._do_save()

            # Verify file exists
            assert state_file.exists()

            # Load and verify content
            with open(state_file) as f:
                data = json.load(f)
            assert data == {"16": 50, "17": 100}

            # Create new manager and verify it loads
            AnalogStateManager._instance = None
            manager2 = AnalogStateManager()
            manager2.configure(state_file)

            assert manager2.get(16) == 50
            assert manager2.get(17) == 100

    def test_configure_changes_state_file(self):
        """Should allow changing state file location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "custom_state.json"

            manager = AnalogStateManager()
            manager.configure(state_file)

            assert manager._state_file == state_file

    def test_load_handles_missing_file(self):
        """Should handle missing state file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "nonexistent.json"

            # Ensure file doesn't exist
            assert not state_file.exists()

            AnalogStateManager._instance = None
            manager = AnalogStateManager()
            # Clear positions that might have loaded from default location
            manager._positions = {}
            # Now configure with nonexistent file
            manager.configure(state_file)

            # Should still have empty positions (file doesn't exist)
            assert manager.get_all() == {}

    def test_load_handles_invalid_json(self):
        """Should handle corrupt state file gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "corrupt.json"
            state_file.write_text("not valid json {{{")

            AnalogStateManager._instance = None
            manager = AnalogStateManager()
            manager.configure(state_file)

            # Should start with empty positions
            assert manager.get_all() == {}

    def test_save_debounce(self):
        """Should debounce rapid saves by scheduling timer."""
        manager = self._get_fresh_manager()

        # Count actual disk writes by tracking file modification
        save_count = [0]
        original_do_save = manager._do_save

        def counting_save():
            save_count[0] += 1
            original_do_save()

        manager._do_save = counting_save

        # First update triggers immediate save
        manager.update(16, 10)
        first_count = save_count[0]
        assert first_count == 1, "First update should trigger immediate save"

        # Rapid subsequent updates should be debounced
        for i in range(5):
            manager.update(16, 20 + i)

        # Should have only 1 save so far (debounced)
        assert save_count[0] == 1, "Rapid updates should be debounced"


class TestAnalogStateIntegration:
    """Integration tests for analog state with other components."""

    def setup_method(self):
        """Reset singleton before each test with isolated state file."""
        AnalogStateManager._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.tmp_dir) / "test_analog_state.json"

    def teardown_method(self):
        """Clean up temp files."""
        import shutil
        if hasattr(self, 'tmp_dir') and Path(self.tmp_dir).exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        AnalogStateManager._instance = None

    def _get_fresh_manager(self) -> AnalogStateManager:
        """Get a fresh manager with isolated state file."""
        AnalogStateManager._instance = None
        manager = AnalogStateManager()
        manager.configure(self.state_file)
        manager._positions = {}
        manager._callbacks = []
        return manager

    def test_callback_receives_correct_values(self):
        """Should pass correct cc and value to callback."""
        manager = self._get_fresh_manager()
        received = []

        def callback(cc: int, value: int) -> None:
            received.append((cc, value))

        manager.register_callback(callback)

        manager.update(16, 0)
        manager.update(17, 127)
        manager.update(18, 64)

        assert received == [(16, 0), (17, 127), (18, 64)]

    def test_boundary_values(self):
        """Should handle boundary values correctly."""
        manager = self._get_fresh_manager()

        # Min value
        manager.update(16, 0)
        assert manager.get(16) == 0

        # Max value
        manager.update(16, 127)
        assert manager.get(16) == 127

        # Exact middle
        manager.update(16, 64)
        assert manager.get(16) == 64
