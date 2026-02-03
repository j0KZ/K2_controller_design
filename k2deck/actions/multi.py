"""Multi-action - Execute sequences of hotkeys with toggle support."""

import logging
import time
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.actions.hotkey import execute_hotkey

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


# Global state tracker for toggle actions (keyed by button note)
_toggle_states: dict[int, bool] = {}


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

        for i, keys in enumerate(sequence):
            if keys:
                try:
                    execute_hotkey(keys)
                    logger.debug("Multi step %d: %s", i + 1, keys)
                except Exception as e:
                    logger.error("Multi step %d failed: %s", i + 1, e)

                # Delay between actions (except after last)
                if i < len(sequence) - 1:
                    time.sleep(delay_sec)


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
        logger.info("Multi-toggle %s → %s (%d steps)", name, state_name, len(sequence))

        for i, keys in enumerate(sequence):
            if keys:
                try:
                    execute_hotkey(keys)
                    logger.debug("Toggle step %d: %s", i + 1, keys)
                except Exception as e:
                    logger.error("Toggle step %d failed: %s", i + 1, e)

                # Delay between actions (except after last)
                if i < len(sequence) - 1:
                    time.sleep(delay_sec)

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
