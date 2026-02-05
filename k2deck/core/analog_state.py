"""Analog State Manager - Persist fader/pot positions.

The K2 is passive MIDI - it cannot report physical positions on connect.
This module persists the last known positions and uses Jump mode for sync:
- On reconnect: UI shows saved positions ("snapshot")
- When user moves a control: immediately jumps to physical value
- May cause audible jumps but ensures PRECISION over smoothness
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Default state file location
DEFAULT_STATE_FILE = Path.home() / ".k2deck" / "analog_state.json"

# Debounce save operations (don't save on every CC message)
SAVE_DEBOUNCE_SECONDS = 1.0


class AnalogStateManager:
    """Singleton manager for analog control positions.

    Features:
    - Persists all fader/pot positions to JSON file
    - Debounced saves (max 1/sec to reduce disk I/O)
    - Callbacks for position changes (WebSocket broadcast)
    - Thread-safe operations
    """

    _instance: "AnalogStateManager | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "AnalogStateManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the manager (only runs once)."""
        if self._initialized:
            return

        self._positions: dict[int, int] = {}  # cc -> value (0-127)
        self._callbacks: list[Callable[[int, int], None]] = []
        self._state_file = DEFAULT_STATE_FILE
        self._save_lock = threading.RLock()  # Reentrant lock to allow nested calls
        self._last_save_time = 0.0
        self._pending_save = False
        self._save_timer: threading.Timer | None = None
        self._initialized = True

        # Load saved state
        self._load()

    def configure(self, state_file: Path | str | None = None) -> None:
        """Configure the state file location.

        Args:
            state_file: Path to state file (default: ~/.k2deck/analog_state.json).
        """
        if state_file:
            self._state_file = Path(state_file)
            self._load()

    def _load(self) -> None:
        """Load saved positions from disk."""
        try:
            if self._state_file.exists():
                with open(self._state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert string keys to int (JSON only supports string keys)
                    self._positions = {int(k): v for k, v in data.items()}
                logger.info(
                    "Loaded %d analog positions from %s",
                    len(self._positions),
                    self._state_file,
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load analog state: %s", e)
            self._positions = {}

    def _save(self) -> None:
        """Save positions to disk (debounced)."""
        with self._save_lock:
            now = time.time()

            # If we recently saved, schedule a delayed save
            if now - self._last_save_time < SAVE_DEBOUNCE_SECONDS:
                if not self._pending_save:
                    self._pending_save = True
                    delay = SAVE_DEBOUNCE_SECONDS - (now - self._last_save_time)
                    self._save_timer = threading.Timer(delay, self._do_save)
                    self._save_timer.daemon = True
                    self._save_timer.start()
                return

            self._do_save()

    def _do_save(self) -> None:
        """Actually write to disk."""
        with self._save_lock:
            self._pending_save = False
            self._last_save_time = time.time()

            try:
                # Ensure directory exists
                self._state_file.parent.mkdir(parents=True, exist_ok=True)

                with open(self._state_file, "w", encoding="utf-8") as f:
                    json.dump(self._positions, f, indent=2)
                logger.debug("Saved analog state to %s", self._state_file)
            except OSError as e:
                logger.error("Failed to save analog state: %s", e)

    def update(self, cc: int, value: int) -> None:
        """Update position of an analog control.

        Called on every CC message from K2.

        Args:
            cc: CC number of the control.
            value: New value (0-127).
        """
        if not 0 <= value <= 127:
            logger.warning("Invalid analog value %d for CC %d", value, cc)
            return

        old_value = self._positions.get(cc)

        # Only update if changed
        if old_value == value:
            return

        self._positions[cc] = value
        logger.debug("Analog CC %d: %d -> %d", cc, old_value or 0, value)

        # Notify callbacks (for WebSocket broadcast)
        for callback in self._callbacks:
            try:
                callback(cc, value)
            except Exception as e:
                logger.error("Analog callback error: %s", e)

        # Schedule save
        self._save()

    def get(self, cc: int) -> int:
        """Get position of a specific control.

        Args:
            cc: CC number of the control.

        Returns:
            Current value (0-127), or 0 if unknown.
        """
        return self._positions.get(cc, 0)

    def get_all(self) -> dict[int, int]:
        """Get all analog positions.

        Returns:
            Dict of cc -> value for all known controls.
        """
        return self._positions.copy()

    def register_callback(self, callback: Callable[[int, int], None]) -> None:
        """Register callback for position changes.

        Callback receives (cc, value) on each change.

        Args:
            callback: Function to call on position change.
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[int, int], None]) -> None:
        """Unregister a callback.

        Args:
            callback: Function to remove.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def reset(self) -> None:
        """Reset all positions to 0."""
        # Cancel any pending save timer
        with self._save_lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
                self._pending_save = False

        self._positions.clear()
        self._save()
        logger.info("Analog state reset")


def get_analog_state_manager() -> AnalogStateManager:
    """Get the analog state manager singleton.

    Returns:
        The AnalogStateManager instance.
    """
    return AnalogStateManager()
