"""Tests for the throttle manager."""

import time

import pytest

from k2deck.core.throttle import FaderDebouncer, ThrottleManager


class TestThrottleManager:
    """Tests for ThrottleManager."""

    def test_first_call_passes(self):
        """First call for a key should always pass."""
        throttle = ThrottleManager(max_hz=10)
        assert throttle.should_process("test_key") is True

    def test_rapid_calls_throttled(self):
        """Rapid calls should be throttled."""
        throttle = ThrottleManager(max_hz=10)  # 100ms interval

        # First call passes
        assert throttle.should_process("key1") is True
        # Immediate second call should be throttled
        assert throttle.should_process("key1") is False

    def test_calls_after_interval_pass(self):
        """Calls after interval should pass."""
        throttle = ThrottleManager(max_hz=100)  # 10ms interval

        assert throttle.should_process("key1") is True
        time.sleep(0.015)  # Wait longer than interval
        assert throttle.should_process("key1") is True

    def test_different_keys_independent(self):
        """Different keys should be throttled independently."""
        throttle = ThrottleManager(max_hz=10)

        assert throttle.should_process("key1") is True
        assert throttle.should_process("key2") is True
        assert throttle.should_process("key1") is False
        assert throttle.should_process("key2") is False

    def test_reset_single_key(self):
        """Reset should clear throttle for a specific key."""
        throttle = ThrottleManager(max_hz=10)

        throttle.should_process("key1")
        throttle.should_process("key2")

        throttle.reset("key1")

        assert throttle.should_process("key1") is True
        assert throttle.should_process("key2") is False

    def test_reset_all_keys(self):
        """Reset with no args should clear all keys."""
        throttle = ThrottleManager(max_hz=10)

        throttle.should_process("key1")
        throttle.should_process("key2")

        throttle.reset()

        assert throttle.should_process("key1") is True
        assert throttle.should_process("key2") is True

    def test_interval_ms_property(self):
        """interval_ms should return correct value."""
        throttle = ThrottleManager(max_hz=50)
        assert throttle.interval_ms == pytest.approx(20.0, rel=0.01)


class TestFaderDebouncer:
    """Tests for FaderDebouncer."""

    def test_debounce_calls_callback_after_delay(self):
        """Callback should be called after delay."""
        debouncer = FaderDebouncer(delay_ms=20)
        results = []

        debouncer.debounce("key1", 100, lambda v: results.append(v))

        # Callback shouldn't fire immediately
        assert results == []

        # Wait for debounce delay
        time.sleep(0.05)
        assert results == [100]

    def test_debounce_only_final_value(self):
        """Rapid calls should only apply final value."""
        debouncer = FaderDebouncer(delay_ms=30)
        results = []

        # Simulate rapid fader movement
        debouncer.debounce("fader1", 10, lambda v: results.append(v))
        debouncer.debounce("fader1", 50, lambda v: results.append(v))
        debouncer.debounce("fader1", 100, lambda v: results.append(v))
        debouncer.debounce("fader1", 127, lambda v: results.append(v))

        # Wait for debounce
        time.sleep(0.06)

        # Only final value should be applied
        assert results == [127]

    def test_different_keys_independent(self):
        """Different keys debounce independently."""
        debouncer = FaderDebouncer(delay_ms=20)
        results = {"a": [], "b": []}

        debouncer.debounce("a", 50, lambda v: results["a"].append(v))
        debouncer.debounce("b", 100, lambda v: results["b"].append(v))

        time.sleep(0.05)

        assert results["a"] == [50]
        assert results["b"] == [100]

    def test_cancel_single_key(self):
        """Cancel should prevent callback for specific key."""
        debouncer = FaderDebouncer(delay_ms=30)
        results = []

        debouncer.debounce("key1", 100, lambda v: results.append(v))
        debouncer.cancel("key1")

        time.sleep(0.05)
        assert results == []

    def test_cancel_all(self):
        """Cancel with no args should cancel all pending."""
        debouncer = FaderDebouncer(delay_ms=30)
        results = []

        debouncer.debounce("key1", 100, lambda v: results.append(("key1", v)))
        debouncer.debounce("key2", 200, lambda v: results.append(("key2", v)))
        debouncer.cancel()

        time.sleep(0.05)
        assert results == []
