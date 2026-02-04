"""Tests for counter.py and counters.py - Counter actions and manager."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from pathlib import Path
import tempfile
import json
import uuid

from k2deck.core.counters import CounterManager, get_counter_manager
from k2deck.actions.counter import CounterAction


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""
    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


def get_temp_file():
    """Get a unique temp file path for each test."""
    return Path(tempfile.gettempdir()) / f"test_counters_{uuid.uuid4().hex}.json"


class TestCounterManager:
    """Test CounterManager class."""

    def setup_method(self):
        """Reset singleton for each test."""
        CounterManager._instance = None

    def test_singleton_pattern(self):
        """Should return same instance."""
        mgr1 = CounterManager()
        mgr2 = CounterManager()
        assert mgr1 is mgr2

    def test_get_counter_manager_returns_singleton(self):
        """get_counter_manager should return singleton."""
        mgr1 = get_counter_manager()
        mgr2 = get_counter_manager()
        assert mgr1 is mgr2

    def test_get_returns_zero_for_new_counter(self):
        """Should return 0 for non-existent counter."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            assert mgr.get("nonexistent") == 0

    def test_set_and_get(self):
        """Should set and get counter value."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            mgr.set("test", 42)
            assert mgr.get("test") == 42

    def test_increment(self):
        """Should increment counter."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            result = mgr.increment("counter1")
            assert result == 1
            result = mgr.increment("counter1")
            assert result == 2

    def test_increment_by_amount(self):
        """Should increment by specified amount."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            result = mgr.increment("counter2", 5)
            assert result == 5
            result = mgr.increment("counter2", 10)
            assert result == 15

    def test_decrement(self):
        """Should decrement counter."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            mgr.set("counter3", 10)
            result = mgr.decrement("counter3")
            assert result == 9

    def test_decrement_below_zero(self):
        """Should allow negative values."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            result = mgr.decrement("counter4", 5)
            assert result == -5

    def test_reset(self):
        """Should reset counter to 0."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            mgr.set("counter5", 100)
            mgr.reset("counter5")
            assert mgr.get("counter5") == 0

    def test_get_all(self):
        """Should return all counters."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            mgr.set("a", 1)
            mgr.set("b", 2)
            all_counters = mgr.get_all()
            assert all_counters["a"] == 1
            assert all_counters["b"] == 2

    def test_callback_on_change(self):
        """Should call callback when counter changes."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            callback = MagicMock()
            mgr.register_callback("watched", callback)
            mgr.set("watched", 42)
            callback.assert_called_once_with(42)

    def test_callback_not_called_for_other_counters(self):
        """Should not call callback for other counters."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            callback = MagicMock()
            mgr.register_callback("watched", callback)
            mgr.set("other", 42)
            callback.assert_not_called()

    def test_unregister_callback(self):
        """Should unregister callback."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = CounterManager()
            callback = MagicMock()
            mgr.register_callback("counter", callback)
            mgr.unregister_callback("counter", callback)
            mgr.set("counter", 42)
            callback.assert_not_called()

    def test_persistence(self):
        """Should persist counters to disk."""
        temp_file = get_temp_file()
        try:
            with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
                mgr = CounterManager()
                mgr.set("persistent", 123)

            # Reset singleton and create new instance
            CounterManager._instance = None

            with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
                mgr2 = CounterManager()
                assert mgr2.get("persistent") == 123
        finally:
            if temp_file.exists():
                temp_file.unlink()


class TestCounterAction:
    """Test CounterAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        CounterManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            action = CounterAction({"name": "test"})
            event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)
            action.execute(event)
            assert get_counter_manager().get("test") == 0

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            action = CounterAction({"name": "test"})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)
            action.execute(event)
            assert get_counter_manager().get("test") == 0

    def test_default_operation_is_increment(self):
        """Should default to increment operation."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            action = CounterAction({"name": "inc_test"})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
            action.execute(event)
            assert get_counter_manager().get("inc_test") == 1

    def test_increment_operation(self):
        """Should increment counter."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            action = CounterAction({"name": "counter", "operation": "increment", "amount": 5})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
            action.execute(event)
            assert get_counter_manager().get("counter") == 5

    def test_decrement_operation(self):
        """Should decrement counter."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = get_counter_manager()
            mgr.set("dec_test", 10)
            action = CounterAction({"name": "dec_test", "operation": "decrement"})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
            action.execute(event)
            assert mgr.get("dec_test") == 9

    def test_reset_operation(self):
        """Should reset counter."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            mgr = get_counter_manager()
            mgr.set("reset_test", 50)
            action = CounterAction({"name": "reset_test", "operation": "reset"})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
            action.execute(event)
            assert mgr.get("reset_test") == 0

    def test_set_operation(self):
        """Should set counter to specific value."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            action = CounterAction({"name": "set_test", "operation": "set", "value": 100})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
            action.execute(event)
            assert get_counter_manager().get("set_test") == 100

    def test_unknown_operation(self):
        """Should handle unknown operation gracefully."""
        temp_file = get_temp_file()
        with patch.object(CounterManager, 'COUNTERS_FILE', temp_file):
            action = CounterAction({"name": "unknown_op", "operation": "invalid"})
            event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)
            # Should not raise
            action.execute(event)
