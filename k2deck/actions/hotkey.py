"""Hotkey action - Keyboard simulation using Windows SendInput API.

Uses hardware scan codes for reliable key simulation that works with
games and apps that ignore virtual key codes.
"""

import logging
import time
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core import keyboard

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


def _focus_target_app(target_app: str | None) -> bool:
    """Focus target app if specified."""
    if not target_app:
        return True
    try:
        from k2deck.actions.window import focus_app

        return focus_app(target_app)
    except ImportError:
        logger.warning("Window focus not available")
        return False


def release_all_modifiers() -> None:
    """Release all modifier keys to prevent stuck keys.

    This is important for multi-action sequences where modifiers
    might get stuck between actions (especially Win key).
    """
    keyboard.release_all_modifiers()


def execute_hotkey(keys: list[str], release_after: bool = True) -> None:
    """Execute a keyboard hotkey combination.

    Uses Windows SendInput API with hardware scan codes for reliable
    key simulation.

    Args:
        keys: List of key names to press simultaneously.
        release_after: If True, release all modifiers after execution.
    """
    if not keys:
        return

    try:
        keyboard.execute_hotkey(keys, hold_ms=15, between_ms=10)

        # Extra safety: release ALL modifiers to prevent stuck keys
        if release_after:
            keyboard.release_all_modifiers()

        logger.debug("Executed hotkey: %s", keys)
    except Exception as e:
        logger.error("Failed to execute hotkey %s: %s", keys, e)
        # Make sure to release ALL held keys
        keyboard.release_all_keys()


class HotkeyAction(Action):
    """Action that simulates keyboard hotkeys.

    Config options:
    - keys: List of key names (e.g., ["ctrl", "shift", "s"])
    - mode: "tap" (default), "hold", or "toggle"
      - tap: Press and release immediately (standard hotkey)
      - hold: Hold while button is pressed, release on button release
      - toggle: First press holds, second press releases
    """

    _toggle_states: dict[int, bool] = {}  # Track toggle state per button

    def execute(self, event: "MidiEvent") -> None:
        """Execute the hotkey based on mode."""
        keys = self.config.get("keys", [])
        if not keys:
            return

        mode = self.config.get("mode", "tap")

        if event.type == "note_on":
            if event.value > 0:
                # Button pressed
                if mode == "tap":
                    self._execute_tap(keys)
                elif mode == "hold":
                    self._execute_hold_start(keys, event.note)
                elif mode == "toggle":
                    self._execute_toggle(keys, event.note)
            else:
                # Button released (note_on with velocity 0)
                if mode == "hold":
                    self._execute_hold_end(keys, event.note)

        elif event.type == "note_off":
            # Button released
            if mode == "hold":
                self._execute_hold_end(keys, event.note)

        elif event.type == "cc":
            # For CC-triggered hotkeys (like media keys on knobs)
            self._execute_tap(keys)

    def _execute_tap(self, keys: list[str]) -> None:
        """Standard tap: press and release immediately."""
        try:
            execute_hotkey(keys)
        except Exception as e:
            logger.error("HotkeyAction tap error: %s", e)

    def _execute_hold_start(self, keys: list[str], note: int) -> None:
        """Start holding keys."""
        try:
            for key in keys:
                keyboard.press_key(key)
            logger.debug("Holding keys: %s", keys)
        except Exception as e:
            logger.error("HotkeyAction hold start error: %s", e)

    def _execute_hold_end(self, keys: list[str], note: int) -> None:
        """Release held keys."""
        try:
            for key in reversed(keys):
                keyboard.release_key(key)
            logger.debug("Released keys: %s", keys)
        except Exception as e:
            logger.error("HotkeyAction hold end error: %s", e)
            keyboard.release_all_keys()

    def _execute_toggle(self, keys: list[str], note: int) -> None:
        """Toggle: first press holds, second press releases."""
        current_state = self._toggle_states.get(note, False)

        try:
            if current_state:
                # Currently held, release
                for key in reversed(keys):
                    keyboard.release_key(key)
                self._toggle_states[note] = False
                logger.debug("Toggle released: %s", keys)
            else:
                # Not held, press and hold
                for key in keys:
                    keyboard.press_key(key)
                self._toggle_states[note] = True
                logger.debug("Toggle pressed: %s", keys)
        except Exception as e:
            logger.error("HotkeyAction toggle error: %s", e)
            keyboard.release_all_keys()
            self._toggle_states[note] = False


class HotkeyRelativeAction(Action):
    """Action for encoder-based directional hotkeys.

    CW rotation triggers "cw" keys, CCW triggers "ccw" keys.

    Config options:
    - cw: keys for clockwise rotation
    - ccw: keys for counter-clockwise rotation
    - target_app: process name to focus before sending keys (e.g., "brave.exe")
    """

    def execute(self, event: "MidiEvent") -> None:
        """Execute directional hotkey based on encoder direction."""
        if event.type != "cc":
            return

        # Focus target app if specified
        target_app = self.config.get("target_app")
        if target_app:
            _focus_target_app(target_app)
            time.sleep(0.05)  # Brief delay for window focus

        # Determine direction from CC value
        # Two's complement: 1-63 = CW, 65-127 = CCW (127 = -1)
        value = event.value

        if 1 <= value <= 63:
            # Clockwise
            keys = self.config.get("cw", [])
            direction = "CW"
        elif 65 <= value <= 127:
            # Counter-clockwise
            keys = self.config.get("ccw", [])
            direction = "CCW"
        else:
            # Value 0 or 64 - ignore
            return

        if keys:
            try:
                execute_hotkey(keys)
                logger.debug("HotkeyRelative %s: %s", direction, keys)
            except Exception as e:
                logger.error("HotkeyRelativeAction error: %s", e)
