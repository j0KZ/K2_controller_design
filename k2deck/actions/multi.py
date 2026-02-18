"""Multi-action - Execute sequences of hotkeys with toggle support.

Uses Windows SendInput API with hardware scan codes for reliable
execution of complex multi-step macro sequences.
"""

import logging
import time
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core import keyboard

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


# Global state tracker for toggle actions (keyed by button note)
_toggle_states: dict[int, bool] = {}
_last_toggle_time: dict[int, float] = {}
_toggle_debounce_ms: float = 300  # Minimum time between toggle presses


class MultiAction(Action):
    """Execute a sequence of hotkeys on button press.

    Config example:
    {
        "name": "Screenshot and paste",
        "action": "multi",
        "sequence": [
            ["win", "shift", "s"],
            ["ctrl", "v"]
        ],
        "delay_ms": 100
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Execute all hotkeys in sequence."""
        if event.type != "note_on" or event.value == 0:
            return

        sequence = self.config.get("sequence", [])
        delay_ms = self.config.get("delay_ms", 50)
        delay_sec = delay_ms / 1000.0

        name = self.config.get("name", "multi")
        logger.info("Executing multi-action: %s (%d steps)", name, len(sequence))

        # Release all modifiers first to prevent stuck keys
        keyboard.release_all_modifiers()
        time.sleep(0.05)

        for i, keys in enumerate(sequence):
            if keys:
                try:
                    keyboard.execute_hotkey(keys, hold_ms=20, between_ms=10)
                    logger.debug("Multi step %d: %s", i + 1, keys)
                except Exception as e:
                    logger.error("Multi step %d failed: %s", i + 1, e)

                # Delay after each action
                time.sleep(delay_sec)

        # Final safety: release all modifiers
        keyboard.release_all_modifiers()


class MultiToggleAction(Action):
    """Toggle between two sequences of hotkeys.

    Perfect for workflows like Discord+Wispr:
    - Press 1: Mute Discord → Start Wispr
    - Press 2: Stop Wispr → Unmute Discord

    Config example:
    {
        "name": "Discord+Wispr Toggle",
        "action": "multi_toggle",
        "on_sequence": [
            ["ctrl", "shift", "m"],
            ["ctrl", "win", "space"]
        ],
        "off_sequence": [
            ["ctrl", "win"],
            ["ctrl", "shift", "m"]
        ],
        "delay_ms": 50,
        "led": { "color": "red", "mode": "toggle", "off_color": "green" }
    }
    """

    def execute(self, event: "MidiEvent") -> None:
        """Execute on_sequence or off_sequence based on current state."""
        if event.type != "note_on" or event.value == 0:
            return

        note = event.note

        # Debounce: prevent rapid double-presses
        now = time.time() * 1000
        last_time = _last_toggle_time.get(note, 0)
        if now - last_time < _toggle_debounce_ms:
            logger.debug("Multi-toggle debounced (too fast)")
            return
        _last_toggle_time[note] = now

        current_state = _toggle_states.get(note, False)

        # Select sequence based on state
        if current_state:
            # Currently ON, execute OFF sequence
            sequence = self.config.get("off_sequence", [])
            new_state = False
            state_name = "OFF"
        else:
            # Currently OFF, execute ON sequence
            sequence = self.config.get("on_sequence", [])
            new_state = True
            state_name = "ON"

        delay_ms = self.config.get("delay_ms", 50)
        delay_sec = delay_ms / 1000.0

        name = self.config.get("name", "multi_toggle")
        logger.info(
            "Multi-toggle %s: was=%s → now=%s (%d steps)",
            name,
            "ON" if current_state else "OFF",
            state_name,
            len(sequence),
        )

        # IMPORTANT: Release all modifiers first to prevent stuck keys
        keyboard.release_all_modifiers()
        time.sleep(0.05)

        for i, keys in enumerate(sequence):
            if keys:
                try:
                    keyboard.execute_hotkey(keys, hold_ms=25, between_ms=15)
                    logger.info("  Step %d: %s", i + 1, keys)
                except Exception as e:
                    logger.error("  Step %d FAILED: %s", i + 1, e)

                # Delay after EVERY action to ensure it registers
                time.sleep(delay_sec)

        # Final safety: release all modifiers again
        keyboard.release_all_modifiers()

        # Update state
        _toggle_states[note] = new_state

    @staticmethod
    def get_state(note: int) -> bool:
        """Get current toggle state for a note."""
        return _toggle_states.get(note, False)

    @staticmethod
    def set_state(note: int, state: bool) -> None:
        """Manually set toggle state (useful for LED sync)."""
        _toggle_states[note] = state

    @staticmethod
    def reset_all() -> None:
        """Reset all toggle states."""
        _toggle_states.clear()
