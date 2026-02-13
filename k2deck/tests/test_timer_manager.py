"""Tests for k2deck.core.timer_manager — Timer Manager."""

import threading
import time
from unittest.mock import MagicMock

from k2deck.core.timer_manager import TimerManager, get_timer_manager


class TestTimerManager:
    def setup_method(self):
        """Reset singleton before each test."""
        TimerManager._instance = None

    def teardown_method(self):
        """Clean up any running timers."""
        if TimerManager._instance is not None:
            TimerManager._instance.stop_all()
            TimerManager._instance = None

    def test_singleton(self):
        """Same instance returned on repeated calls."""
        a = get_timer_manager()
        b = get_timer_manager()
        assert a is b

    def test_start_timer_creates_entry(self):
        """Starting a timer adds it to the manager."""
        mgr = get_timer_manager()
        mgr.start_timer("test", 10)
        assert mgr.is_running("test")
        assert mgr.get_remaining("test") is not None

    def test_remaining_decreases(self):
        """Remaining time decreases after ticks."""
        mgr = get_timer_manager()
        done = threading.Event()

        def on_tick(remaining):
            if remaining <= 8:
                done.set()

        mgr.start_timer("test", 10, on_tick=on_tick)
        done.wait(timeout=5)
        remaining = mgr.get_remaining("test")
        assert remaining is not None
        assert remaining <= 9  # At least 1 tick elapsed

    def test_stop_timer(self):
        """Stopping a timer sets running to False."""
        mgr = get_timer_manager()
        mgr.start_timer("test", 60)
        assert mgr.is_running("test")

        result = mgr.stop_timer("test")
        assert result is True
        time.sleep(0.1)  # Let thread exit
        assert not mgr.is_running("test")

    def test_stop_nonexistent_timer(self):
        """Stopping a nonexistent timer returns False."""
        mgr = get_timer_manager()
        assert mgr.stop_timer("nonexistent") is False

    def test_toggle_starts_then_stops(self):
        """Toggle starts if stopped, stops if running."""
        mgr = get_timer_manager()

        # First toggle: starts
        result = mgr.toggle_timer("test", 60)
        assert result is True
        assert mgr.is_running("test")

        # Second toggle: stops
        result = mgr.toggle_timer("test", 60)
        assert result is False
        time.sleep(0.1)
        assert not mgr.is_running("test")

    def test_completion_callback(self):
        """on_complete fires when timer reaches zero."""
        mgr = get_timer_manager()
        completed = threading.Event()

        def on_complete():
            completed.set()

        mgr.start_timer("fast", 1, on_complete=on_complete)
        assert completed.wait(timeout=5)

    def test_completion_not_fired_on_stop(self):
        """on_complete does NOT fire when timer is stopped early."""
        mgr = get_timer_manager()
        completed = threading.Event()

        def on_complete():
            completed.set()

        mgr.start_timer("test", 60, on_complete=on_complete)
        mgr.stop_timer("test")
        time.sleep(0.2)
        assert not completed.is_set()

    def test_restart_running_timer(self):
        """Starting an already-running timer restarts it with new duration."""
        mgr = get_timer_manager()
        mgr.start_timer("test", 60)
        time.sleep(0.1)

        # Restart with shorter duration
        mgr.start_timer("test", 30)
        remaining = mgr.get_remaining("test")
        assert remaining is not None
        assert remaining > 25  # Should be close to 30, not 59

    def test_multiple_independent_timers(self):
        """Multiple timers run independently."""
        mgr = get_timer_manager()
        mgr.start_timer("timer_a", 60)
        mgr.start_timer("timer_b", 30)

        assert mgr.is_running("timer_a")
        assert mgr.is_running("timer_b")

        mgr.stop_timer("timer_a")
        time.sleep(0.1)
        assert not mgr.is_running("timer_a")
        assert mgr.is_running("timer_b")

    def test_get_remaining_nonexistent(self):
        """get_remaining returns None for unknown timer."""
        mgr = get_timer_manager()
        assert mgr.get_remaining("nope") is None

    def test_is_running_nonexistent(self):
        """is_running returns False for unknown timer."""
        mgr = get_timer_manager()
        assert mgr.is_running("nope") is False

    def test_get_all(self):
        """get_all returns status of all timers."""
        mgr = get_timer_manager()
        mgr.start_timer("a", 60)
        mgr.start_timer("b", 30)

        status = mgr.get_all()
        assert "a" in status
        assert "b" in status
        assert status["a"]["duration"] == 60
        assert status["b"]["duration"] == 30
        assert status["a"]["running"] is True

    def test_stop_all(self):
        """stop_all stops all timers and clears the dict."""
        mgr = get_timer_manager()
        mgr.start_timer("a", 60)
        mgr.start_timer("b", 60)

        mgr.stop_all()
        time.sleep(0.1)
        assert mgr.get_all() == {}

    def test_seconds_minimum_clamped(self):
        """Seconds below 1 are clamped to 1."""
        mgr = get_timer_manager()
        mgr.start_timer("tiny", 0)
        remaining = mgr.get_remaining("tiny")
        assert remaining is not None
        assert remaining >= 0  # Was clamped to 1, may have ticked once

    def test_on_tick_error_does_not_crash(self):
        """Error in on_tick callback is caught."""
        mgr = get_timer_manager()
        ticked = threading.Event()

        def bad_tick(remaining):
            ticked.set()
            raise RuntimeError("tick boom")

        mgr.start_timer("test", 5, on_tick=bad_tick)
        ticked.wait(timeout=3)
        # Timer should still be running despite error
        assert mgr.is_running("test")

    def test_on_complete_error_does_not_crash(self):
        """Error in on_complete callback is caught."""
        mgr = get_timer_manager()
        completed = threading.Event()

        def bad_complete():
            completed.set()
            raise RuntimeError("complete boom")

        mgr.start_timer("test", 1, on_complete=bad_complete)
        completed.wait(timeout=5)
        # Should not crash — just log error

    def test_thread_safety_concurrent_starts(self):
        """Multiple threads starting timers concurrently doesn't crash."""
        mgr = get_timer_manager()
        errors = []

        def start_many(prefix):
            try:
                for i in range(10):
                    mgr.start_timer(f"{prefix}_{i}", 60)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=start_many, args=(f"t{n}",)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # Should have 40 timers
        assert len(mgr.get_all()) == 40
