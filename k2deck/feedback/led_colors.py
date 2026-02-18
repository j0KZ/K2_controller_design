"""LED color constants and helpers for the Xone:K2.

CRITICAL: K2 LEDs are controlled by NOTE NUMBER, not velocity.

Each button has 3 MIDI notes (one per color). The color is determined by
adding an offset to the button's base note number:

    Red:   base_note + 0
    Amber: base_note + 36
    Green: base_note + 72

Example for button at note 36:
    Red:   Note On 36  (36 + 0)
    Amber: Note On 72  (36 + 36)
    Green: Note On 108 (36 + 72)

Verified in Mixxx source: XoneK2.color = { red: 0, amber: 36, green: 72 }
Verified in VirtualDJ mappings.
"""

from typing import Literal

# Color offset constants (add to base note)
COLOR_OFFSET_RED = 0
COLOR_OFFSET_AMBER = 36
COLOR_OFFSET_GREEN = 72

# Color offsets as dict for lookup
COLOR_OFFSETS: dict[str, int] = {
    "red": COLOR_OFFSET_RED,
    "amber": COLOR_OFFSET_AMBER,
    "green": COLOR_OFFSET_GREEN,
}

# Valid color names
ColorName = Literal["red", "amber", "green", "off"]


def led_note(base_note: int, color: str) -> int:
    """Convert button base note + color to the actual MIDI note to send.

    Args:
        base_note: The button's base MIDI note number.
        color: Color name ("red", "amber", "green").

    Returns:
        The MIDI note number to send for that color.

    Raises:
        ValueError: If color is not valid.
    """
    if color not in COLOR_OFFSETS:
        raise ValueError(
            f"Invalid color: {color}. Must be one of: {list(COLOR_OFFSETS.keys())}"
        )
    return base_note + COLOR_OFFSETS[color]


def base_note_from_led(led_note_number: int) -> tuple[int, str]:
    """Determine base note and color from any LED note number.

    Args:
        led_note_number: The MIDI note number (could be red, amber, or green).

    Returns:
        Tuple of (base_note, color_name).

    Note:
        Assumes notes are in valid K2 range. For notes >= 72, checks green first.
    """
    # Try each offset to find which color range this note is in
    if led_note_number >= COLOR_OFFSET_GREEN:
        return (led_note_number - COLOR_OFFSET_GREEN, "green")
    elif led_note_number >= COLOR_OFFSET_AMBER:
        return (led_note_number - COLOR_OFFSET_AMBER, "amber")
    else:
        return (led_note_number - COLOR_OFFSET_RED, "red")


def get_all_led_notes(base_note: int) -> dict[str, int]:
    """Get all LED note numbers for a button.

    Args:
        base_note: The button's base MIDI note number.

    Returns:
        Dict mapping color names to their MIDI note numbers.
    """
    return {
        "red": base_note + COLOR_OFFSET_RED,
        "amber": base_note + COLOR_OFFSET_AMBER,
        "green": base_note + COLOR_OFFSET_GREEN,
    }
