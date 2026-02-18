"""LED Manager - State machine for K2 LED control.

Manages LED states, toggle behavior, and flash animations.
Thread-safe for use with concurrent action execution.
"""

import logging
import threading
import time
from typing import TYPE_CHECKING

from k2deck.feedback.led_colors import COLOR_OFFSETS, led_note

if TYPE_CHECKING:
    from k2deck.core.midi_output import MidiOutput

logger = logging.getLogger(__name__)


class LedManager:
    """Manages LED state and control for the K2."""

    def __init__(
        self,
        midi_output: "MidiOutput",
        color_offsets: dict[str, int] | None = None,
    ):
        """Initialize LED manager.

        Args:
            midi_output: MidiOutput instance for sending LED commands.
            color_offsets: Optional custom color offsets. Uses defaults if None.
        """
        self._output = midi_output
        self._offsets = color_offsets or COLOR_OFFSETS.copy()

        # State tracking: base_note -> current color (or None if off)
        self._state: dict[int, str | None] = {}
        self._lock = threading.Lock()

    def set_led(self, base_note: int, color: str) -> None:
        """Set LED to a specific color.

        Args:
            base_note: Button's base MIDI note number.
            color: Color name ("red", "amber", "green", "off").
        """
        with self._lock:
            if color == "off":
                self._turn_off(base_note)
            else:
                note = led_note(base_note, color)
                if self._output.send_note_on(note):
                    self._state[base_note] = color
                    logger.debug("LED %d set to %s (note %d)", base_note, color, note)

    def _turn_off(self, base_note: int) -> None:
        """Turn off LED (internal, assumes lock held)."""
        # Send note off on all color notes to ensure it's off
        for color in self._offsets:
            note = led_note(base_note, color)
            self._output.send_note_off(note)
        self._state[base_note] = None
        logger.debug("LED %d turned off", base_note)

    def turn_off(self, base_note: int) -> None:
        """Turn off LED at base note."""
        with self._lock:
            self._turn_off(base_note)

    # Alias for route compatibility
    set_led_off = turn_off

    def toggle_led(
        self,
        base_note: int,
        on_color: str,
        off_color: str = "off",
    ) -> bool:
        """Toggle LED between on and off states.

        Args:
            base_note: Button's base MIDI note number.
            on_color: Color when "on" ("red", "amber", "green").
            off_color: Color when "off" ("red", "amber", "green", "off").

        Returns:
            True if LED is now in "on" state, False if "off".
        """
        with self._lock:
            current = self._state.get(base_note)

            if current == on_color:
                # Currently on -> turn off
                if off_color == "off":
                    self._turn_off(base_note)
                else:
                    note = led_note(base_note, off_color)
                    if self._output.send_note_on(note):
                        self._state[base_note] = off_color
                return False
            else:
                # Currently off -> turn on
                note = led_note(base_note, on_color)
                if self._output.send_note_on(note):
                    self._state[base_note] = on_color
                return True

    def flash_led(
        self,
        base_note: int,
        color: str,
        times: int = 3,
        interval: float = 0.15,
    ) -> None:
        """Flash LED a number of times, then return to previous state.

        Runs in a separate thread to avoid blocking.

        Args:
            base_note: Button's base MIDI note number.
            color: Color to flash ("red", "amber", "green").
            times: Number of flashes.
            interval: Seconds between on/off transitions.
        """

        def flash_thread():
            with self._lock:
                previous_color = self._state.get(base_note)

            note = led_note(base_note, color)

            for _ in range(times):
                self._output.send_note_on(note)
                time.sleep(interval)
                self._output.send_note_off(note)
                time.sleep(interval)

            # Restore previous state
            with self._lock:
                if previous_color:
                    restore_note = led_note(base_note, previous_color)
                    self._output.send_note_on(restore_note)
                    self._state[base_note] = previous_color
                else:
                    self._state[base_note] = None

        thread = threading.Thread(target=flash_thread, daemon=True)
        thread.start()

    def all_off(self) -> None:
        """Turn off all tracked LEDs."""
        with self._lock:
            for base_note in list(self._state.keys()):
                self._turn_off(base_note)
            self._state.clear()
        logger.info("All LEDs turned off")

    def get_state(self, base_note: int) -> str | None:
        """Get current state of an LED.

        Args:
            base_note: Button's base MIDI note number.

        Returns:
            Current color name or None if off.
        """
        with self._lock:
            return self._state.get(base_note)

    def get_all_states(self) -> dict[int, str]:
        """Get all active LED states.

        Returns:
            Dict of base_note -> color for LEDs that are on.
        """
        with self._lock:
            return {k: v for k, v in self._state.items() if v is not None}

    def restore_defaults(self, defaults: list[dict]) -> None:
        """Restore LEDs to default states.

        Args:
            defaults: List of dicts with "note" and "color" keys.
        """
        for item in defaults:
            note = item.get("note")
            color = item.get("color")
            if note is not None and color:
                self.set_led(note, color)
        logger.info("Restored %d default LED states", len(defaults))

    def startup_animation(self, notes: list[int], delay: float = 0.05) -> None:
        """Play a startup animation across LEDs.

        Args:
            notes: List of base notes to animate.
            delay: Delay between each LED.
        """

        def animation_thread():
            # Sweep green
            for note in notes:
                led = led_note(note, "green")
                self._output.send_note_on(led)
                time.sleep(delay)

            time.sleep(0.3)

            # All off
            for note in notes:
                for color in self._offsets:
                    led = led_note(note, color)
                    self._output.send_note_off(led)

        thread = threading.Thread(target=animation_thread, daemon=True)
        thread.start()


# =============================================================================
# Singleton accessor
# =============================================================================

_led_manager: LedManager | None = None


def get_led_manager() -> LedManager:
    """Get or create the global LedManager singleton.

    Returns:
        The shared LedManager instance.

    Raises:
        RuntimeError: If no LedManager has been initialized.
    """
    global _led_manager
    if _led_manager is None:
        raise RuntimeError("LedManager not initialized. Call init_led_manager() first.")
    return _led_manager


def init_led_manager(midi_output: "MidiOutput") -> LedManager:
    """Initialize the global LedManager singleton.

    Args:
        midi_output: MidiOutput instance for sending LED commands.

    Returns:
        The initialized LedManager instance.
    """
    global _led_manager
    _led_manager = LedManager(midi_output)
    return _led_manager
