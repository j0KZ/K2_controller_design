"""Counter Manager - Persistent counters for tracking.

Provides increment/decrement/reset operations with JSON persistence.
Useful for tracking kills, reps, pomodoros, etc.
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class CounterManager:
    """Manages persistent counters.

    Singleton pattern ensures all actions share the same state.
    Counters persist to ~/.k2deck/counters.json.
    """

    _instance: "CounterManager | None" = None
    COUNTERS_FILE = Path.home() / ".k2deck" / "counters.json"

    def __new__(cls) -> "CounterManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the counter manager (only runs once)."""
        if self._initialized:
            return

        self._counters: dict[str, int] = {}
        self._callbacks: dict[str, list[Callable[[int], None]]] = {}
        self._load()
        self._initialized = True

    def _load(self) -> None:
        """Load counters from disk."""
        try:
            if self.COUNTERS_FILE.exists():
                self._counters = json.loads(self.COUNTERS_FILE.read_text())
                logger.info("Loaded %d counters", len(self._counters))
        except Exception as e:
            logger.warning("Failed to load counters: %s", e)
            self._counters = {}

    def _save(self) -> None:
        """Save counters to disk."""
        try:
            self.COUNTERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.COUNTERS_FILE.write_text(json.dumps(self._counters, indent=2))
        except Exception as e:
            logger.error("Failed to save counters: %s", e)

    def get(self, name: str) -> int:
        """Get counter value.

        Args:
            name: Counter name.

        Returns:
            Counter value (0 if not exists).
        """
        return self._counters.get(name, 0)

    def set(self, name: str, value: int) -> None:
        """Set counter value.

        Args:
            name: Counter name.
            value: New value.
        """
        self._counters[name] = value
        self._save()
        self._notify(name, value)
        logger.info("Counter '%s' = %d", name, value)

    def increment(self, name: str, amount: int = 1) -> int:
        """Increment counter.

        Args:
            name: Counter name.
            amount: Amount to add (default: 1).

        Returns:
            New counter value.
        """
        value = self.get(name) + amount
        self.set(name, value)
        return value

    def decrement(self, name: str, amount: int = 1) -> int:
        """Decrement counter.

        Args:
            name: Counter name.
            amount: Amount to subtract (default: 1).

        Returns:
            New counter value.
        """
        value = self.get(name) - amount
        self.set(name, value)
        return value

    def reset(self, name: str) -> None:
        """Reset counter to 0.

        Args:
            name: Counter name.
        """
        self.set(name, 0)

    def get_all(self) -> dict[str, int]:
        """Get all counters.

        Returns:
            Dictionary of all counter names and values.
        """
        return self._counters.copy()

    def register_callback(self, name: str, callback: Callable[[int], None]) -> None:
        """Register callback for counter changes.

        Args:
            name: Counter name to watch.
            callback: Function to call with new value.
        """
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

    def unregister_callback(self, name: str, callback: Callable[[int], None]) -> None:
        """Unregister a callback.

        Args:
            name: Counter name.
            callback: Function to remove.
        """
        if name in self._callbacks and callback in self._callbacks[name]:
            self._callbacks[name].remove(callback)

    def _notify(self, name: str, value: int) -> None:
        """Notify callbacks for counter change.

        Args:
            name: Counter name.
            value: New value.
        """
        for callback in self._callbacks.get(name, []):
            try:
                callback(value)
            except Exception as e:
                logger.error("Counter callback error: %s", e)


def get_counter_manager() -> CounterManager:
    """Get the counter manager singleton.

    Returns:
        The CounterManager instance.
    """
    return CounterManager()
