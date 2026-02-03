"""Hotkey action - Keyboard simulation using pynput."""

import logging
import time
from typing import TYPE_CHECKING

from pynput.keyboard import Controller, Key, KeyCode

from k2deck.actions.base import Action

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

# Keyboard controller singleton
_keyboard = Controller()

# Key name to pynput Key mapping
KEY_MAP: dict[str, Key | str] = {
    # Modifiers
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "alt": Key.alt,
    "shift": Key.shift,
    "win": Key.cmd,
    "cmd": Key.cmd,
    "super": Key.cmd,
    # Special keys
    "space": Key.space,
    "enter": Key.enter,
    "return": Key.enter,
    "tab": Key.tab,
    "escape": Key.esc,
    "esc": Key.esc,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "del": Key.delete,
    "insert": Key.insert,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "page_up": Key.page_up,
    "pagedown": Key.page_down,
    "page_down": Key.page_down,
    # Arrow keys
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    # Function keys
    "f1": Key.f1,
    "f2": Key.f2,
    "f3": Key.f3,
    "f4": Key.f4,
    "f5": Key.f5,
    "f6": Key.f6,
    "f7": Key.f7,
    "f8": Key.f8,
    "f9": Key.f9,
    "f10": Key.f10,
    "f11": Key.f11,
    "f12": Key.f12,
    "f13": Key.f13,
    "f14": Key.f14,
    "f15": Key.f15,
    "f16": Key.f16,
    "f17": Key.f17,
    "f18": Key.f18,
    "f19": Key.f19,
    "f20": Key.f20,
    # Media keys
    "media_play_pause": Key.media_play_pause,
    "media_next": Key.media_next,
    "media_previous": Key.media_previous,
    "volume_up": Key.media_volume_up,
    "volume_down": Key.media_volume_down,
    "volume_mute": Key.media_volume_mute,
    # Misc
    "print_screen": Key.print_screen,
    "scroll_lock": Key.scroll_lock,
    "pause": Key.pause,
    "caps_lock": Key.caps_lock,
    "num_lock": Key.num_lock,
    "menu": Key.menu,
}


def parse_key(key_name: str) -> Key | KeyCode:
    """Convert key name string to pynput key.

    Args:
        key_name: Key name (e.g., "ctrl", "a", "f5").

    Returns:
        pynput Key or KeyCode.
    """
    key_lower = key_name.lower()

    # Check special keys
    if key_lower in KEY_MAP:
        key = KEY_MAP[key_lower]
        if isinstance(key, str):
            return KeyCode.from_char(key)
        return key

    # Single character
    if len(key_name) == 1:
        return KeyCode.from_char(key_name)

    # Try as character code (for special chars)
    logger.warning("Unknown key: %s, treating as character", key_name)
    return KeyCode.from_char(key_name[0])


def execute_hotkey(keys: list[str]) -> None:
    """Execute a keyboard hotkey combination.

    Args:
        keys: List of key names to press simultaneously.
    """
    parsed_keys = [parse_key(k) for k in keys]

    # Separate modifiers and regular keys
    modifiers = []
    regular = []
    for k in parsed_keys:
        if isinstance(k, Key) and k in (Key.ctrl, Key.alt, Key.shift, Key.cmd):
            modifiers.append(k)
        else:
            regular.append(k)

    try:
        # Press modifiers first
        for mod in modifiers:
            _keyboard.press(mod)

        # Press and release regular keys
        for key in regular:
            _keyboard.press(key)
            _keyboard.release(key)

        # Release modifiers in reverse order
        for mod in reversed(modifiers):
            _keyboard.release(mod)

        logger.debug("Executed hotkey: %s", keys)
    except Exception as e:
        logger.error("Failed to execute hotkey %s: %s", keys, e)
        # Make sure to release any held keys
        for mod in modifiers:
            try:
                _keyboard.release(mod)
            except Exception:
                pass


class HotkeyAction(Action):
    """Action that simulates keyboard hotkeys."""

    def execute(self, event: "MidiEvent") -> None:
        """Execute the hotkey.

        Only triggers on Note On with velocity > 0.
        """
        # Only trigger on actual press (Note On with velocity)
        if event.type == "note_on" and event.value > 0:
            keys = self.config.get("keys", [])
            if keys:
                try:
                    execute_hotkey(keys)
                except Exception as e:
                    logger.error("HotkeyAction error: %s", e)
        elif event.type == "cc":
            # For CC-triggered hotkeys (like media keys on knobs)
            keys = self.config.get("keys", [])
            if keys:
                try:
                    execute_hotkey(keys)
                except Exception as e:
                    logger.error("HotkeyAction CC error: %s", e)


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
