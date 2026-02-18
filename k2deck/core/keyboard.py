"""Windows SendInput keyboard simulation with hardware scan codes.

This module provides low-level keyboard simulation using the Windows SendInput API
with hardware scan codes (KEYEVENTF_SCANCODE). This is the same approach used by
Stream Deck and other professional macro tools.

Benefits over pynput/virtual key codes:
- More reliable for complex key combinations
- Works with games and anti-cheat systems
- Properly releases keys without getting stuck
- Hardware-level simulation
"""

import ctypes
import logging
import threading
import time
from ctypes import Structure, Union, c_long, c_ulong, c_ushort, sizeof

logger = logging.getLogger(__name__)

# Windows API constants
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

INPUT_KEYBOARD = 1


# Windows API structures
class KEYBDINPUT(Structure):
    _fields_ = [
        ("wVk", c_ushort),
        ("wScan", c_ushort),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", ctypes.POINTER(c_ulong)),
    ]


class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", ctypes.POINTER(c_ulong)),
    ]


class HARDWAREINPUT(Structure):
    _fields_ = [
        ("uMsg", c_ulong),
        ("wParamL", c_ushort),
        ("wParamH", c_ushort),
    ]


class INPUT_UNION(Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(Structure):
    _fields_ = [
        ("type", c_ulong),
        ("union", INPUT_UNION),
    ]


# Load user32.dll
user32 = ctypes.windll.user32

# Scan code mappings
# Reference: https://www.win.tue.nl/~aeb/linux/kbd/scancodes-1.html
SCAN_CODES: dict[str, tuple[int, bool]] = {
    # Letters (value, is_extended)
    "a": (0x1E, False),
    "b": (0x30, False),
    "c": (0x2E, False),
    "d": (0x20, False),
    "e": (0x12, False),
    "f": (0x21, False),
    "g": (0x22, False),
    "h": (0x23, False),
    "i": (0x17, False),
    "j": (0x24, False),
    "k": (0x25, False),
    "l": (0x26, False),
    "m": (0x32, False),
    "n": (0x31, False),
    "o": (0x18, False),
    "p": (0x19, False),
    "q": (0x10, False),
    "r": (0x13, False),
    "s": (0x1F, False),
    "t": (0x14, False),
    "u": (0x16, False),
    "v": (0x2F, False),
    "w": (0x11, False),
    "x": (0x2D, False),
    "y": (0x15, False),
    "z": (0x2C, False),
    # Numbers (top row)
    "0": (0x0B, False),
    "1": (0x02, False),
    "2": (0x03, False),
    "3": (0x04, False),
    "4": (0x05, False),
    "5": (0x06, False),
    "6": (0x07, False),
    "7": (0x08, False),
    "8": (0x09, False),
    "9": (0x0A, False),
    # Function keys
    "f1": (0x3B, False),
    "f2": (0x3C, False),
    "f3": (0x3D, False),
    "f4": (0x3E, False),
    "f5": (0x3F, False),
    "f6": (0x40, False),
    "f7": (0x41, False),
    "f8": (0x42, False),
    "f9": (0x43, False),
    "f10": (0x44, False),
    "f11": (0x57, False),
    "f12": (0x58, False),
    # Modifiers
    "ctrl": (0x1D, False),  # Left Ctrl
    "ctrl_l": (0x1D, False),
    "ctrl_r": (0x1D, True),  # Right Ctrl (extended)
    "alt": (0x38, False),  # Left Alt
    "alt_l": (0x38, False),
    "alt_r": (0x38, True),  # Right Alt (extended) - AltGr
    "shift": (0x2A, False),  # Left Shift
    "shift_l": (0x2A, False),
    "shift_r": (0x36, False),  # Right Shift
    "win": (0x5B, True),  # Left Windows (extended)
    "win_l": (0x5B, True),
    "win_r": (0x5C, True),  # Right Windows (extended)
    "cmd": (0x5B, True),  # Alias for Win
    # Special keys
    "space": (0x39, False),
    "enter": (0x1C, False),
    "return": (0x1C, False),
    "tab": (0x0F, False),
    "backspace": (0x0E, False),
    "escape": (0x01, False),
    "esc": (0x01, False),
    # Navigation (extended keys)
    "insert": (0x52, True),
    "delete": (0x53, True),
    "home": (0x47, True),
    "end": (0x4F, True),
    "pageup": (0x49, True),
    "page_up": (0x49, True),
    "pagedown": (0x51, True),
    "page_down": (0x51, True),
    # Arrow keys (extended)
    "up": (0x48, True),
    "down": (0x50, True),
    "left": (0x4B, True),
    "right": (0x4D, True),
    # Punctuation and symbols
    "`": (0x29, False),
    "~": (0x29, False),
    "-": (0x0C, False),
    "_": (0x0C, False),
    "=": (0x0D, False),
    "+": (0x0D, False),
    "[": (0x1A, False),
    "{": (0x1A, False),
    "]": (0x1B, False),
    "}": (0x1B, False),
    "\\": (0x2B, False),
    "|": (0x2B, False),
    ";": (0x27, False),
    ":": (0x27, False),
    "'": (0x28, False),
    '"': (0x28, False),
    ",": (0x33, False),
    "<": (0x33, False),
    ".": (0x34, False),
    ">": (0x34, False),
    "/": (0x35, False),
    "?": (0x35, False),
    # Numpad
    "numpad0": (0x52, False),
    "numpad1": (0x4F, False),
    "numpad2": (0x50, False),
    "numpad3": (0x51, False),
    "numpad4": (0x4B, False),
    "numpad5": (0x4C, False),
    "numpad6": (0x4D, False),
    "numpad7": (0x47, False),
    "numpad8": (0x48, False),
    "numpad9": (0x49, False),
    "numpad_add": (0x4E, False),
    "numpad_subtract": (0x4A, False),
    "numpad_multiply": (0x37, False),
    "numpad_divide": (0x35, True),
    "numpad_enter": (0x1C, True),
    "numpad_decimal": (0x53, False),
    "numlock": (0x45, False),
    # System keys
    "printscreen": (0x37, True),
    "print_screen": (0x37, True),
    "scrolllock": (0x46, False),
    "scroll_lock": (0x46, False),
    "pause": (0x45, True),
    "capslock": (0x3A, False),
    "caps_lock": (0x3A, False),
    # Media keys (scan codes via special handling)
    "media_play_pause": (0x22, True),
    "media_stop": (0x24, True),
    "media_next": (0x19, True),
    "media_previous": (0x10, True),
    "media_prev": (0x10, True),
    "volume_up": (0x30, True),
    "volume_down": (0x2E, True),
    "volume_mute": (0x20, True),
}

# Virtual key codes for media keys (SendInput needs VK for some media keys)
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_MUTE = 0xAD

# Media keys need virtual key codes, not scan codes
MEDIA_VK_CODES: dict[str, int] = {
    "media_play_pause": VK_MEDIA_PLAY_PAUSE,
    "media_stop": VK_MEDIA_STOP,
    "media_next": VK_MEDIA_NEXT_TRACK,
    "media_previous": VK_MEDIA_PREV_TRACK,
    "media_prev": VK_MEDIA_PREV_TRACK,
    "volume_up": VK_VOLUME_UP,
    "volume_down": VK_VOLUME_DOWN,
    "volume_mute": VK_VOLUME_MUTE,
}

# Modifier keys for tracking state
MODIFIER_KEYS = {
    "ctrl",
    "ctrl_l",
    "ctrl_r",
    "alt",
    "alt_l",
    "alt_r",
    "shift",
    "shift_l",
    "shift_r",
    "win",
    "win_l",
    "win_r",
    "cmd",
}

# Thread safety
_lock = threading.Lock()

# State tracking
_held_keys: set[str] = set()


def _send_input(inputs: list[INPUT]) -> int:
    """Send inputs to Windows.

    Args:
        inputs: List of INPUT structures.

    Returns:
        Number of events successfully inserted.
    """
    n_inputs = len(inputs)
    input_array = (INPUT * n_inputs)(*inputs)
    return user32.SendInput(n_inputs, input_array, sizeof(INPUT))


def _create_key_input(scan_code: int, extended: bool, key_up: bool) -> INPUT:
    """Create a keyboard INPUT structure.

    Args:
        scan_code: Hardware scan code.
        extended: Whether this is an extended key (arrows, right ctrl, etc.).
        key_up: True for key release, False for key press.

    Returns:
        INPUT structure ready for SendInput.
    """
    flags = KEYEVENTF_SCANCODE
    if extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if key_up:
        flags |= KEYEVENTF_KEYUP

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = 0
    inp.union.ki.wScan = scan_code
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None

    return inp


def _create_vk_input(vk_code: int, key_up: bool) -> INPUT:
    """Create a keyboard INPUT structure using virtual key code.

    Used for media keys which don't work with scan codes.

    Args:
        vk_code: Virtual key code.
        key_up: True for key release, False for key press.

    Returns:
        INPUT structure ready for SendInput.
    """
    flags = 0
    if key_up:
        flags |= KEYEVENTF_KEYUP

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk_code
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = None

    return inp


def press_key(key: str) -> bool:
    """Press a key (without releasing).

    Args:
        key: Key name (e.g., "a", "ctrl", "f5").

    Returns:
        True if successful, False otherwise.
    """
    key_lower = key.lower()

    with _lock:
        # Check for media keys (use VK codes)
        if key_lower in MEDIA_VK_CODES:
            vk_code = MEDIA_VK_CODES[key_lower]
            inp = _create_vk_input(vk_code, key_up=False)
            result = _send_input([inp])
            if result > 0:
                _held_keys.add(key_lower)
            return result > 0

        # Regular keys use scan codes
        if key_lower not in SCAN_CODES:
            logger.warning("Unknown key: %s", key)
            return False

        scan_code, extended = SCAN_CODES[key_lower]
        inp = _create_key_input(scan_code, extended, key_up=False)
        result = _send_input([inp])

        if result > 0:
            _held_keys.add(key_lower)

        return result > 0


def release_key(key: str) -> bool:
    """Release a key.

    Args:
        key: Key name (e.g., "a", "ctrl", "f5").

    Returns:
        True if successful, False otherwise.
    """
    key_lower = key.lower()

    with _lock:
        # Check for media keys (use VK codes)
        if key_lower in MEDIA_VK_CODES:
            vk_code = MEDIA_VK_CODES[key_lower]
            inp = _create_vk_input(vk_code, key_up=True)
            result = _send_input([inp])
            _held_keys.discard(key_lower)
            return result > 0

        # Regular keys use scan codes
        if key_lower not in SCAN_CODES:
            logger.warning("Unknown key: %s", key)
            return False

        scan_code, extended = SCAN_CODES[key_lower]
        inp = _create_key_input(scan_code, extended, key_up=True)
        result = _send_input([inp])

        _held_keys.discard(key_lower)
        return result > 0


def tap_key(key: str, hold_ms: float = 10) -> bool:
    """Press and release a key.

    Args:
        key: Key name.
        hold_ms: Milliseconds to hold the key.

    Returns:
        True if successful, False otherwise.
    """
    if not press_key(key):
        return False
    time.sleep(hold_ms / 1000.0)
    return release_key(key)


def execute_hotkey(keys: list[str], hold_ms: float = 10, between_ms: float = 5) -> bool:
    """Execute a hotkey combination.

    Presses all keys in sequence, holds, then releases in reverse order.

    Args:
        keys: List of key names (e.g., ["ctrl", "shift", "s"]).
        hold_ms: Milliseconds to hold the combination.
        between_ms: Milliseconds between key presses.

    Returns:
        True if all keys were pressed successfully.
    """
    if not keys:
        return True

    logger.debug("SendInput hotkey: %s", keys)

    pressed: list[str] = []
    success = True

    try:
        # Press all keys in order
        for key in keys:
            if press_key(key):
                pressed.append(key)
                time.sleep(between_ms / 1000.0)
            else:
                logger.error("Failed to press key: %s", key)
                success = False
                break

        # Hold the combination
        if pressed:
            time.sleep(hold_ms / 1000.0)

    finally:
        # Release in reverse order
        for key in reversed(pressed):
            release_key(key)
            time.sleep(between_ms / 1000.0)

    return success


def release_all_modifiers() -> None:
    """Release all modifier keys to prevent stuck keys.

    This is critical for preventing stuck Ctrl, Alt, Shift, Win keys
    after complex sequences.
    """
    modifiers = [
        "ctrl",
        "ctrl_l",
        "ctrl_r",
        "alt",
        "alt_l",
        "alt_r",
        "shift",
        "shift_l",
        "shift_r",
        "win",
        "win_l",
        "win_r",
    ]

    with _lock:
        for mod in modifiers:
            if mod in SCAN_CODES:
                scan_code, extended = SCAN_CODES[mod]
                inp = _create_key_input(scan_code, extended, key_up=True)
                _send_input([inp])

        # Clear tracked held keys for modifiers
        for mod in modifiers:
            _held_keys.discard(mod)

    logger.debug("Released all modifiers")


def release_all_keys() -> None:
    """Release all currently held keys."""
    with _lock:
        held = list(_held_keys)

    for key in held:
        release_key(key)

    # Also release all modifiers just to be safe
    release_all_modifiers()


def get_held_keys() -> set[str]:
    """Get set of currently held keys."""
    with _lock:
        return _held_keys.copy()


def is_key_held(key: str) -> bool:
    """Check if a key is currently held."""
    with _lock:
        return key.lower() in _held_keys


def type_text(text: str, delay_ms: float = 10) -> bool:
    """Type a string of text.

    Note: Only supports characters that have direct scan codes.
    For Unicode text, use clipboard paste instead.

    Args:
        text: Text to type.
        delay_ms: Delay between characters.

    Returns:
        True if all characters were typed successfully.
    """
    for char in text:
        char_lower = char.lower()

        # Check if we need shift for uppercase or symbols
        needs_shift = char.isupper() or char in '~!@#$%^&*()_+{}|:"<>?'

        if needs_shift:
            press_key("shift")
            time.sleep(delay_ms / 1000.0)

        if not tap_key(char_lower, hold_ms=delay_ms):
            logger.warning("Could not type character: %s", char)
            if needs_shift:
                release_key("shift")
            return False

        if needs_shift:
            release_key("shift")

        time.sleep(delay_ms / 1000.0)

    return True


# Test function
def test_keyboard() -> None:
    """Test keyboard simulation. Press Ctrl+C to cancel."""
    import sys

    print("Testing SendInput keyboard simulation...")
    print("Will type 'hello' in 3 seconds. Focus a text editor!")
    print("Press Ctrl+C to cancel.")

    try:
        time.sleep(3)

        print("Typing 'hello'...")
        type_text("hello")

        print("\nTesting Ctrl+A (select all)...")
        time.sleep(1)
        execute_hotkey(["ctrl", "a"])

        print("\nTest complete!")

    except KeyboardInterrupt:
        print("\nCancelled.")
        release_all_keys()
        sys.exit(0)


if __name__ == "__main__":
    test_keyboard()
