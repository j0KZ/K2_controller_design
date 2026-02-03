"""Mouse scroll action - Scroll simulation using pynput."""

import logging
import time
from typing import TYPE_CHECKING

from pynput.mouse import Controller

from k2deck.actions.base import Action

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)

# Mouse controller singleton
_mouse = Controller()


def _focus_target_app(target_app: str | None) -> bool:
    """Focus target app if specified.

    Returns True if focus was successful or no target specified.
    """
    if not target_app:
        return True

    try:
        from k2deck.actions.window import focus_app

        return focus_app(target_app)
    except ImportError:
        logger.warning("Window focus not available")
        return False


class MouseScrollAction(Action):
    """Action that simulates mouse scroll from encoder rotation.

    Scroll direction is determined by encoder CC value:
    - 1-63: Clockwise
    - 65-127: Counter-clockwise

    Config options:
    - step: scroll amount per tick (default: 3)
    - invert: if true, CW=down, CCW=up (default: true, like a volume knob)
    - acceleration: if true, faster rotation = more scroll (default: false)
    - target_app: process name to focus before scrolling (e.g., "Discord.exe")
    """

    def execute(self, event: "MidiEvent") -> None:
        """Execute mouse scroll based on encoder direction."""
        if event.type != "cc":
            return

        # Focus target app if specified
        target_app = self.config.get("target_app")
        if target_app:
            _focus_target_app(target_app)
            time.sleep(0.05)  # Brief delay for window focus

        step = self.config.get("step", 3)
        invert = self.config.get("invert", True)  # Default inverted (like volume knob)
        value = event.value

        try:
            if 1 <= value <= 63:
                # Clockwise
                scroll_amount = step
                if self.config.get("acceleration", False):
                    scroll_amount = step * min(value, 5)

                if invert:
                    _mouse.scroll(0, -scroll_amount)  # CW = down
                    logger.debug("Scroll down: %d", scroll_amount)
                else:
                    _mouse.scroll(0, scroll_amount)   # CW = up
                    logger.debug("Scroll up: %d", scroll_amount)

            elif 65 <= value <= 127:
                # Counter-clockwise
                scroll_amount = step
                if self.config.get("acceleration", False):
                    scroll_amount = step * min(128 - value, 5)

                if invert:
                    _mouse.scroll(0, scroll_amount)   # CCW = up
                    logger.debug("Scroll up: %d", scroll_amount)
                else:
                    _mouse.scroll(0, -scroll_amount)  # CCW = down
                    logger.debug("Scroll down: %d", scroll_amount)

        except Exception as e:
            logger.error("MouseScrollAction error: %s", e)
