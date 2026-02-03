"""Mouse scroll action - Scroll simulation using pynput."""

import logging
from typing import TYPE_CHECKING

from pynput.mouse import Controller

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)

# Mouse controller singleton
_mouse = Controller()


class MouseScrollAction(Action):
    """Action that simulates mouse scroll from encoder rotation.

    Scroll direction is determined by encoder CC value:
    - 1-63: Clockwise = scroll up
    - 65-127: Counter-clockwise = scroll down
    """

    def execute(self, event: "MidiEvent") -> None:
        """Execute mouse scroll based on encoder direction."""
        if event.type != "cc":
            return

        step = self.config.get("step", 3)
        value = event.value

        try:
            if 1 <= value <= 63:
                # Clockwise = scroll up
                # Multiply step by value for acceleration (optional)
                scroll_amount = step
                if self.config.get("acceleration", False):
                    scroll_amount = step * min(value, 5)
                _mouse.scroll(0, scroll_amount)
                logger.debug("Scroll up: %d", scroll_amount)

            elif 65 <= value <= 127:
                # Counter-clockwise = scroll down
                scroll_amount = step
                if self.config.get("acceleration", False):
                    scroll_amount = step * min(128 - value, 5)
                _mouse.scroll(0, -scroll_amount)
                logger.debug("Scroll down: %d", scroll_amount)

        except Exception as e:
            logger.error("MouseScrollAction error: %s", e)
