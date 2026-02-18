"""Timer Manager - Countdown timers with completion callbacks.

Manages named timers that count down in background threads.
Timers are transient (not persisted to disk).
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TimerState:
    """State of a single timer."""

    name: str
    duration: float
    remaining: float
    running: bool = True
    _stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    on_tick: Callable[[float], None] | None = (
        None  # Reserved for future WebSocket tick broadcast
    )
    on_complete: Callable[[], None] | None = None


class TimerManager:
    """Manages countdown timers.

    Singleton pattern ensures all actions share the same state.
    Timers are transient — they do not survive a restart.
    """

    _instance: "TimerManager | None" = None

    def __new__(cls) -> "TimerManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the timer manager (only runs once)."""
        if self._initialized:
            return

        self._timers: dict[str, TimerState] = {}
        self._lock = threading.Lock()
        self._initialized = True

    def start_timer(
        self,
        name: str,
        seconds: float,
        on_tick: Callable[[float], None] | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Start a countdown timer.

        If a timer with the same name is already running, it is stopped
        and restarted with the new duration.

        Args:
            name: Timer identifier.
            seconds: Countdown duration in seconds (minimum 1).
            on_tick: Called every second with remaining time.
            on_complete: Called when timer reaches zero.
        """
        seconds = max(1.0, float(seconds))

        with self._lock:
            # Stop existing timer with same name
            if name in self._timers and self._timers[name].running:
                self._timers[name].running = False
                self._timers[name]._stop_event.set()

            state = TimerState(
                name=name,
                duration=seconds,
                remaining=seconds,
                on_tick=on_tick,
                on_complete=on_complete,
            )
            self._timers[name] = state

            thread = threading.Thread(
                target=self._run_timer,
                args=(state,),
                daemon=True,
                name=f"timer-{name}",
            )
            state.thread = thread
            thread.start()

        logger.info("Timer '%s' started: %.0fs", name, seconds)

    def _run_timer(self, state: TimerState) -> None:
        """Timer thread loop. Ticks every 1s until stopped or complete."""
        while state.running and state.remaining > 0:
            state._stop_event.wait(1.0)
            if not state.running:
                break
            state.remaining = max(0.0, state.remaining - 1.0)

            if state.on_tick and state.running:
                try:
                    state.on_tick(state.remaining)
                except Exception as e:
                    logger.error("Timer '%s' on_tick error: %s", state.name, e)

        # Fire completion callback only if timer ran to zero (not stopped)
        if state.remaining <= 0 and state.running:
            state.running = False
            logger.info("Timer '%s' completed", state.name)
            if state.on_complete:
                try:
                    state.on_complete()
                except Exception as e:
                    logger.error("Timer '%s' on_complete error: %s", state.name, e)

    def stop_timer(self, name: str) -> bool:
        """Stop a running timer.

        Args:
            name: Timer identifier.

        Returns:
            True if timer was running and stopped, False otherwise.
        """
        with self._lock:
            state = self._timers.get(name)
            if state and state.running:
                state.running = False
                state._stop_event.set()
                logger.info(
                    "Timer '%s' stopped (%.0fs remaining)", name, state.remaining
                )
                return True
        return False

    def toggle_timer(
        self,
        name: str,
        seconds: float,
        on_tick: Callable[[float], None] | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> bool:
        """Toggle a timer: stop if running, start if stopped.

        Args:
            name: Timer identifier.
            seconds: Duration for start (ignored if stopping).
            on_tick: Called every second with remaining time.
            on_complete: Called when timer reaches zero.

        Returns:
            True if timer was started, False if stopped.
        """
        with self._lock:
            state = self._timers.get(name)
            if state and state.running:
                state.running = False
                state._stop_event.set()
                logger.info("Timer '%s' toggled off", name)
                return False

        # Start outside lock (start_timer acquires its own lock)
        self.start_timer(name, seconds, on_tick, on_complete)
        return True

    def get_remaining(self, name: str) -> float | None:
        """Get remaining seconds for a timer.

        Args:
            name: Timer identifier.

        Returns:
            Remaining seconds, or None if timer doesn't exist.
        """
        state = self._timers.get(name)
        if state is None:
            return None
        return state.remaining

    def is_running(self, name: str) -> bool:
        """Check if a timer is currently running.

        Args:
            name: Timer identifier.

        Returns:
            True if timer exists and is running.
        """
        state = self._timers.get(name)
        return state is not None and state.running

    def get_all(self) -> dict[str, dict]:
        """Get status of all timers.

        Returns:
            Dictionary of timer names to status dicts.
        """
        result = {}
        for name, state in self._timers.items():
            result[name] = {
                "duration": state.duration,
                "remaining": state.remaining,
                "running": state.running,
            }
        return result

    def stop_all(self) -> None:
        """Stop all running timers (call on app shutdown)."""
        with self._lock:
            for state in self._timers.values():
                if state.running:
                    state.running = False
                    state._stop_event.set()
            self._timers.clear()
        logger.info("All timers stopped")


def get_timer_manager() -> TimerManager:
    """Get the timer manager singleton.

    Returns:
        The TimerManager instance.
    """
    return TimerManager()
