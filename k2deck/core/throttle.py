"""Throttle manager for rate-limiting CC messages.

Faders can send 60+ messages/sec. Without throttling, this hammers pycaw
and the Windows Audio API. This module rate-limits processing to a
configurable max Hz.
"""

import time
from collections.abc import Callable
from threading import Lock, Timer
from typing import Any


class FaderDebouncer:
    """Debouncer that ensures final fader values are always applied.

    When faders move fast, intermediate values may be throttled. This class
    stores the last value and applies it after movement stops, ensuring
    0 (min) and 127 (max) are never lost.
    """

    def __init__(self, delay_ms: float = 50.0):
        """Initialize fader debouncer.

        Args:
            delay_ms: Delay in milliseconds before applying final value.
        """
        self._delay = delay_ms / 1000.0
        self._pending: dict[str, tuple[int, Timer, Callable[[int], Any]]] = {}
        self._lock = Lock()

    def debounce(self, key: str, value: int, callback: Callable[[int], Any]) -> None:
        """Store value and schedule callback after delay.

        If called again before delay expires, cancels previous timer and
        reschedules with new value.

        Args:
            key: Unique identifier for the fader (e.g., "cc_16").
            value: The fader value (0-127).
            callback: Function to call with the final value.
        """
        with self._lock:
            # Cancel existing timer for this key
            if key in self._pending:
                _, old_timer, _ = self._pending[key]
                old_timer.cancel()

            # Create new timer
            timer = Timer(self._delay, self._execute, args=[key])
            self._pending[key] = (value, timer, callback)
            timer.start()

    def _execute(self, key: str) -> None:
        """Execute the callback with stored value."""
        with self._lock:
            if key not in self._pending:
                return
            value, _, callback = self._pending.pop(key)

        # Execute outside lock to avoid blocking
        try:
            callback(value)
        except Exception:
            pass  # Callback errors are handled elsewhere

    def cancel(self, key: str | None = None) -> None:
        """Cancel pending debounced calls.

        Args:
            key: Specific key to cancel, or None to cancel all.
        """
        with self._lock:
            if key is None:
                for _, timer, _ in self._pending.values():
                    timer.cancel()
                self._pending.clear()
            elif key in self._pending:
                _, timer, _ = self._pending.pop(key)
                timer.cancel()


class ThrottleManager:
    """Rate limiter for high-frequency events like fader movements."""

    def __init__(self, max_hz: int = 30):
        """Initialize throttle manager.

        Args:
            max_hz: Maximum calls per second allowed per key.
        """
        self._last_call: dict[str, float] = {}
        self._interval = 1.0 / max_hz
        self._lock = Lock()

    def should_process(self, key: str) -> bool:
        """Check if enough time has passed since last call for this key.

        Args:
            key: Unique identifier for the event source (e.g., "cc_1").

        Returns:
            True if the event should be processed, False if throttled.
        """
        now = time.monotonic()
        with self._lock:
            last = self._last_call.get(key, 0.0)
            if now - last < self._interval:
                return False
            self._last_call[key] = now
            return True

    def reset(self, key: str | None = None) -> None:
        """Reset throttle state.

        Args:
            key: Specific key to reset, or None to reset all.
        """
        with self._lock:
            if key is None:
                self._last_call.clear()
            elif key in self._last_call:
                del self._last_call[key]

    @property
    def interval_ms(self) -> float:
        """Get the throttle interval in milliseconds."""
        return self._interval * 1000
