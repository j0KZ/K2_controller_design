"""K2 Layer Management - Software layer support for Xone:K2.

The Xone:K2 has 3 hardware layers (cycling via button 15), but hardware
layers are limited. This module provides software layer support that gives
full flexibility:

- 3 layers (or more if needed)
- Per-button layer-specific mappings
- Layer sections can be independent or repeat
- Layer state tracked in software
- LED feedback for current layer

Hardware Layer Button:
- Note 15 cycles through layers on the K2
- We intercept this to manage software layers
"""

import logging
import threading
from collections.abc import Callable
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class Layer(IntEnum):
    """Layer identifiers."""

    LAYER_1 = 1
    LAYER_2 = 2
    LAYER_3 = 3


# Layer button (cycles through layers)
LAYER_BUTTON_NOTE = 15

# Thread lock for layer state
_lock = threading.Lock()

# Callbacks for layer change notifications
_layer_change_callbacks: list[Callable[[int], None]] = []

# Current layer state
_current_layer: int = 1
_layer_count: int = 3


def get_current_layer() -> int:
    """Get current active layer (1-based)."""
    with _lock:
        return _current_layer


def set_layer(layer: int) -> bool:
    """Set the current layer.

    Args:
        layer: Layer number (1-based, typically 1-3).

    Returns:
        True if layer changed, False if invalid or same.
    """
    global _current_layer

    with _lock:
        if layer < 1 or layer > _layer_count:
            logger.warning("Invalid layer: %d (must be 1-%d)", layer, _layer_count)
            return False

        if layer == _current_layer:
            return False

        old_layer = _current_layer
        _current_layer = layer
        new_layer = _current_layer
        callbacks = _layer_change_callbacks.copy()

    logger.info("Layer changed: %d -> %d", old_layer, new_layer)

    # Notify callbacks (outside lock to prevent deadlocks)
    for callback in callbacks:
        try:
            callback(new_layer)
        except Exception as e:
            logger.error("Layer change callback error: %s", e)

    return True


def cycle_layer() -> int:
    """Cycle to the next layer.

    Returns:
        New layer number.
    """
    with _lock:
        next_layer = (_current_layer % _layer_count) + 1
    set_layer(next_layer)
    return get_current_layer()


def get_layer_count() -> int:
    """Get the number of configured layers."""
    with _lock:
        return _layer_count


def set_layer_count(count: int) -> None:
    """Set the number of layers (default 3).

    Args:
        count: Number of layers (minimum 1).
    """
    global _layer_count, _current_layer

    if count < 1:
        logger.warning("Invalid layer count: %d (must be >= 1)", count)
        return

    with _lock:
        _layer_count = count
        # Clamp current layer if needed
        if _current_layer > _layer_count:
            _current_layer = 1


def register_layer_change_callback(callback: Callable[[int], None]) -> None:
    """Register a callback for layer changes.

    Callback receives the new layer number.
    """
    with _lock:
        if callback not in _layer_change_callbacks:
            _layer_change_callbacks.append(callback)


def unregister_layer_change_callback(callback: Callable[[int], None]) -> None:
    """Unregister a layer change callback."""
    with _lock:
        if callback in _layer_change_callbacks:
            _layer_change_callbacks.remove(callback)


def is_layer_button(note: int) -> bool:
    """Check if a note is the layer button."""
    return note == LAYER_BUTTON_NOTE


def handle_layer_button(event: "MidiEvent") -> bool:
    """Handle layer button press.

    Args:
        event: MIDI event.

    Returns:
        True if this was a layer button event (consumed), False otherwise.
    """
    if event.type != "note_on" or event.value == 0:
        return False

    if event.note != LAYER_BUTTON_NOTE:
        return False

    # Cycle to next layer
    new_layer = cycle_layer()
    logger.info("Layer button pressed -> Layer %d", new_layer)

    return True


def resolve_layer_mapping(mapping_config: dict | None, note_or_cc: int) -> dict | None:
    """Resolve mapping based on current layer.

    Config can have layer-specific mappings:
    {
        "36": {
            "name": "Button A1",
            "layer_1": { "action": "hotkey", "keys": ["f1"] },
            "layer_2": { "action": "hotkey", "keys": ["f2"] },
            "layer_3": { "action": "spotify_play_pause" },
            "led": { ... }  # Shared LED config
        }
    }

    Or a simple mapping (same for all layers):
    {
        "36": {
            "name": "Button A1",
            "action": "hotkey",
            "keys": ["f1"]
        }
    }

    Args:
        mapping_config: The raw mapping config for this note/CC.
        note_or_cc: The note or CC number (for logging).

    Returns:
        Layer-resolved mapping config, or None if no mapping.
    """
    if mapping_config is None:
        return None

    layer_key = f"layer_{get_current_layer()}"

    # Check for layer-specific mapping
    if layer_key in mapping_config:
        layer_mapping = mapping_config[layer_key].copy()

        # Merge shared properties (like LED config, name)
        for key in ["name", "led"]:
            if key in mapping_config and key not in layer_mapping:
                layer_mapping[key] = mapping_config[key]

        logger.debug(
            "Layer %d mapping for %d: %s",
            get_current_layer(),
            note_or_cc,
            layer_mapping.get("name", "unnamed"),
        )
        return layer_mapping

    # Check if any layer-specific keys exist (meaning other layers are defined)
    has_layer_keys = any(k.startswith("layer_") for k in mapping_config.keys())

    if has_layer_keys:
        # Has layer configs but not for current layer - no mapping
        logger.debug("No mapping for layer %d on %d", get_current_layer(), note_or_cc)
        return None

    # Simple mapping - same for all layers
    return mapping_config


def get_layer_led_color(layer: int | None = None) -> str:
    """Get LED color for layer indicator.

    Args:
        layer: Layer number (uses current if None).

    Returns:
        Color name for the layer.
    """
    if layer is None:
        layer = get_current_layer()

    # Color coding: Layer 1 = green, Layer 2 = amber, Layer 3 = red
    colors = {1: "green", 2: "amber", 3: "red"}
    return colors.get(layer, "amber")


def reset() -> None:
    """Reset layer state to default."""
    global _current_layer
    with _lock:
        _current_layer = 1
    logger.debug("Layer state reset to 1")
