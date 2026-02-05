"""K2 Hardware State API Routes.

Endpoints:
- GET  /api/k2/layout        - K2 hardware layout (grid, control types)
- GET  /api/k2/state         - Complete state (LEDs, layer, folder, connection)
- GET  /api/k2/state/leds    - All LED states
- PUT  /api/k2/state/leds/{note} - Set LED color
- GET  /api/k2/state/layer   - Current layer
- PUT  /api/k2/state/layer   - Set layer
- GET  /api/k2/state/folder  - Current folder
- GET  /api/k2/state/analog  - All analog positions
- GET  /api/k2/midi/devices  - List MIDI devices
- GET  /api/k2/midi/status   - K2 connection status
- POST /api/k2/midi/reconnect - Force reconnect
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from k2deck.core.analog_state import get_analog_state_manager
from k2deck.core.folders import get_folder_manager
from k2deck.core.layers import get_current_layer, set_layer

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# K2 Hardware Layout
# =============================================================================

# Official Xone:K2 layout from Allen & Heath documentation
K2_LAYOUT = {
    "rows": [
        # Row 0: Encoders (4x, with push button + LED)
        {
            "type": "encoder-row",
            "controls": [
                {"id": "E1", "type": "encoder", "hasLed": True, "hasPush": True, "cc": 0, "pushNote": 32},
                {"id": "E2", "type": "encoder", "hasLed": True, "hasPush": True, "cc": 1, "pushNote": 33},
                {"id": "E3", "type": "encoder", "hasLed": True, "hasPush": True, "cc": 2, "pushNote": 34},
                {"id": "E4", "type": "encoder", "hasLed": True, "hasPush": True, "cc": 3, "pushNote": 35},
            ],
        },
        # Row 1-3: Potentiometers (12x, 3 rows of 4)
        {
            "type": "pot-row",
            "controls": [
                {"id": "P1", "type": "pot", "cc": 4},
                {"id": "P2", "type": "pot", "cc": 5},
                {"id": "P3", "type": "pot", "cc": 6},
                {"id": "P4", "type": "pot", "cc": 7},
            ],
        },
        {
            "type": "pot-row",
            "controls": [
                {"id": "P5", "type": "pot", "cc": 8},
                {"id": "P6", "type": "pot", "cc": 9},
                {"id": "P7", "type": "pot", "cc": 10},
                {"id": "P8", "type": "pot", "cc": 11},
            ],
        },
        {
            "type": "pot-row",
            "controls": [
                {"id": "P9", "type": "pot", "cc": 12},
                {"id": "P10", "type": "pot", "cc": 13},
                {"id": "P11", "type": "pot", "cc": 14},
                {"id": "P12", "type": "pot", "cc": 15},
            ],
        },
        # Row 4-7: Button grid (16x, 4 rows of 4) with tri-color LEDs
        {
            "type": "button-row",
            "controls": [
                {"id": "A", "type": "button", "note": 36, "hasLed": True, "ledNotes": {"red": 36, "amber": 72, "green": 108}},
                {"id": "B", "type": "button", "note": 37, "hasLed": True, "ledNotes": {"red": 37, "amber": 73, "green": 109}},
                {"id": "C", "type": "button", "note": 38, "hasLed": True, "ledNotes": {"red": 38, "amber": 74, "green": 110}},
                {"id": "D", "type": "button", "note": 39, "hasLed": True, "ledNotes": {"red": 39, "amber": 75, "green": 111}},
            ],
        },
        {
            "type": "button-row",
            "controls": [
                {"id": "E", "type": "button", "note": 40, "hasLed": True, "ledNotes": {"red": 40, "amber": 76, "green": 112}},
                {"id": "F", "type": "button", "note": 41, "hasLed": True, "ledNotes": {"red": 41, "amber": 77, "green": 113}},
                {"id": "G", "type": "button", "note": 42, "hasLed": True, "ledNotes": {"red": 42, "amber": 78, "green": 114}},
                {"id": "H", "type": "button", "note": 43, "hasLed": True, "ledNotes": {"red": 43, "amber": 79, "green": 115}},
            ],
        },
        {
            "type": "button-row",
            "controls": [
                {"id": "I", "type": "button", "note": 44, "hasLed": True, "ledNotes": {"red": 44, "amber": 80, "green": 116}},
                {"id": "J", "type": "button", "note": 45, "hasLed": True, "ledNotes": {"red": 45, "amber": 81, "green": 117}},
                {"id": "K", "type": "button", "note": 46, "hasLed": True, "ledNotes": {"red": 46, "amber": 82, "green": 118}},
                {"id": "L", "type": "button", "note": 47, "hasLed": True, "ledNotes": {"red": 47, "amber": 83, "green": 119}},
            ],
        },
        {
            "type": "button-row",
            "controls": [
                {"id": "M", "type": "button", "note": 48, "hasLed": True, "ledNotes": {"red": 48, "amber": 84, "green": 120}},
                {"id": "N", "type": "button", "note": 49, "hasLed": True, "ledNotes": {"red": 49, "amber": 85, "green": 121}},
                {"id": "O", "type": "button", "note": 50, "hasLed": True, "ledNotes": {"red": 50, "amber": 86, "green": 122}},
                {"id": "P", "type": "button", "note": 51, "hasLed": True, "ledNotes": {"red": 51, "amber": 87, "green": 123}},
            ],
        },
        # Row 8: Faders (4x)
        {
            "type": "fader-row",
            "controls": [
                {"id": "F1", "type": "fader", "cc": 16},
                {"id": "F2", "type": "fader", "cc": 17},
                {"id": "F3", "type": "fader", "cc": 18},
                {"id": "F4", "type": "fader", "cc": 19},
            ],
        },
        # Row 9: Control row (Layer + 2 Encoders + Exit)
        {
            "type": "control-row",
            "controls": [
                {"id": "LAYER", "type": "button", "note": 15, "hasLed": True, "special": "layer"},
                {"id": "E5", "type": "encoder", "hasLed": True, "hasPush": True, "cc": 20, "pushNote": 52},
                {"id": "E6", "type": "encoder", "hasLed": True, "hasPush": True, "cc": 21, "pushNote": 53},
                {"id": "EXIT", "type": "button", "note": 14, "hasLed": False, "special": "exit"},
            ],
        },
    ],
    "totalControls": 52,
    "totalLeds": 34,
    "layers": 3,
    "midiChannel": 16,
}


class LedState(BaseModel):
    """LED state."""

    note: int
    color: str | None  # "red", "amber", "green", or None (off)
    on: bool


class LayerUpdate(BaseModel):
    """Request body for layer change."""

    layer: int


class K2State(BaseModel):
    """Complete K2 state."""

    connected: bool
    port: str | None
    layer: int
    folder: str | None
    leds: dict[int, str]  # note -> color
    analog: dict[int, int]  # cc -> value


class MidiDevice(BaseModel):
    """MIDI device info."""

    name: str
    type: str  # "input" or "output"


class MidiStatus(BaseModel):
    """K2 connection status."""

    connected: bool
    port: str | None
    error: str | None


# =============================================================================
# Layout Endpoint
# =============================================================================


@router.get("/layout")
async def get_layout() -> dict[str, Any]:
    """Get K2 hardware layout.

    Returns:
        Complete K2 layout with all controls, their types, and MIDI mappings.
    """
    return K2_LAYOUT


# =============================================================================
# State Endpoints
# =============================================================================


@router.get("/state")
async def get_state() -> K2State:
    """Get complete K2 state.

    Returns:
        K2State with connection, layer, folder, LEDs, and analog positions.
    """
    # Get LED states
    try:
        from k2deck.feedback.led_manager import get_led_manager

        led_manager = get_led_manager()
        leds = led_manager.get_all_states()
    except Exception:
        leds = {}

    # Get analog positions
    analog_manager = get_analog_state_manager()
    analog = analog_manager.get_all()

    # Get folder state
    folder_manager = get_folder_manager()
    folder = folder_manager.current_folder

    # Get connection status
    # TODO: Get from MIDI listener
    connected = False
    port = None

    return K2State(
        connected=connected,
        port=port,
        layer=get_current_layer(),
        folder=folder,
        leds=leds,
        analog=analog,
    )


@router.get("/state/leds")
async def get_led_states() -> dict[int, str]:
    """Get all LED states.

    Returns:
        Dict of note -> color for all active LEDs.
    """
    try:
        from k2deck.feedback.led_manager import get_led_manager

        led_manager = get_led_manager()
        return led_manager.get_all_states()
    except Exception as e:
        logger.error("Failed to get LED states: %s", e)
        return {}


# Valid LED notes on K2:
# - Encoder push buttons: 32-35 (E1-E4)
# - Main buttons: 36-51 (A-P)
# - Bottom encoders: 52-53 (E5-E6)
# - Layer button: 15
VALID_LED_NOTES = set(range(32, 54)) | {15}


@router.put("/state/leds/{note}")
async def set_led_state(note: int, body: LedState) -> dict[str, str]:
    """Set LED color for a button.

    Args:
        note: Base note of the LED (32-53 for buttons/encoders, 15 for layer).
        body: LED state with color.

    Returns:
        Success message.

    Raises:
        HTTPException: If note is out of valid range.
    """
    # Validate note is within K2 LED range
    if note not in VALID_LED_NOTES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid LED note: {note}. Valid notes: 15 (layer), 32-53 (buttons/encoders)",
        )

    # Validate color if provided
    if body.on and body.color and body.color not in ("red", "amber", "green"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid LED color: {body.color}. Valid colors: red, amber, green",
        )

    try:
        from k2deck.feedback.led_manager import get_led_manager

        led_manager = get_led_manager()

        if body.on and body.color:
            led_manager.set_led(note, body.color)
        else:
            led_manager.set_led_off(note)

        return {"message": f"LED {note} set to {body.color if body.on else 'off'}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set LED: {e}")


@router.get("/state/layer")
async def get_layer_state() -> dict[str, int]:
    """Get current layer.

    Returns:
        Current layer number (1-based).
    """
    return {"layer": get_current_layer()}


@router.put("/state/layer")
async def set_layer_state(body: LayerUpdate) -> dict[str, Any]:
    """Set current layer.

    Args:
        body: Layer update with new layer number.

    Returns:
        Result with previous layer.
    """
    previous = get_current_layer()

    if not set_layer(body.layer):
        raise HTTPException(
            status_code=400, detail=f"Invalid layer: {body.layer} (must be 1-3)"
        )

    return {"layer": body.layer, "previous": previous}


@router.get("/state/folder")
async def get_folder_state() -> dict[str, str | None]:
    """Get current folder.

    Returns:
        Current folder name or None for root.
    """
    folder_manager = get_folder_manager()
    return {"folder": folder_manager.current_folder}


@router.get("/state/analog")
async def get_analog_state() -> dict[int, int]:
    """Get all analog control positions.

    Returns:
        Dict of cc -> value (0-127) for all analog controls.
    """
    analog_manager = get_analog_state_manager()
    return analog_manager.get_all()


# =============================================================================
# MIDI Endpoints
# =============================================================================


@router.get("/midi/devices")
async def get_midi_devices() -> list[MidiDevice]:
    """List available MIDI devices.

    Returns:
        List of MIDI devices (inputs and outputs).
    """
    devices: list[MidiDevice] = []

    try:
        import mido

        # Input devices
        for name in mido.get_input_names():
            devices.append(MidiDevice(name=name, type="input"))

        # Output devices
        for name in mido.get_output_names():
            if name not in [d.name for d in devices if d.type == "input"]:
                devices.append(MidiDevice(name=name, type="output"))
            else:
                # Mark as bidirectional
                for d in devices:
                    if d.name == name:
                        d.type = "bidirectional"

    except Exception as e:
        logger.error("Failed to list MIDI devices: %s", e)

    return devices


@router.get("/midi/status")
async def get_midi_status() -> MidiStatus:
    """Get K2 connection status.

    Returns:
        Connection status with port name and any error.
    """
    # TODO: Get from MIDI listener
    return MidiStatus(connected=False, port=None, error=None)


@router.post("/midi/reconnect")
async def reconnect_midi() -> dict[str, str]:
    """Force MIDI reconnection.

    Returns:
        Result message.
    """
    # TODO: Trigger reconnect in MIDI listener
    return {"message": "Reconnection triggered"}
