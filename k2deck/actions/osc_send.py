"""OSC Send actions - Forward MIDI events to Pure Data via OSC.

Three variants for the three MIDI event types:
- OscSendAction: cc_absolute (faders/pots) → normalize, curve, scale, send
- OscSendRelativeAction: cc_relative (encoders) → accumulate deltas, clip, send
- OscSendTriggerAction: note_on (buttons) → bang or toggle, send
"""

import logging
import threading
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.osc import OscSender

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


def _apply_curve(normalized: float, curve: str) -> float:
    """Apply response curve to normalized 0.0-1.0 value.

    Args:
        normalized: Input value in 0.0-1.0 range.
        curve: "linear" or "exponential".

    Returns:
        Curved value in 0.0-1.0 range.
    """
    if curve == "exponential":
        return normalized ** 3
    return normalized


def _scale_to_range(normalized: float, min_val: float, max_val: float) -> float:
    """Scale 0.0-1.0 value to target range.

    Args:
        normalized: Value in 0.0-1.0.
        min_val: Target minimum.
        max_val: Target maximum.

    Returns:
        Scaled value.
    """
    return min_val + normalized * (max_val - min_val)


class OscSendAction(Action):
    """Forward CC absolute values (faders/pots) to Pd via OSC.

    Normalizes MIDI 0-127 → 0.0-1.0 → applies curve → scales to [min, max].

    Config:
        osc_host: Target host (default: "127.0.0.1")
        osc_port: Target UDP port (default: 9000)
        osc_address: OSC address pattern (default: "/pd/param")
        osc_param: Parameter bus name (e.g., "synth__p__cutoff")
        min: Minimum output value (default: 0.0)
        max: Maximum output value (default: 1.0)
        curve: "linear" (default) or "exponential"
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._host = config.get("osc_host", "127.0.0.1")
        self._port = config.get("osc_port", 9000)
        self._address = config.get("osc_address", "/pd/param")
        self._param = config.get("osc_param", "")
        self._min = float(config.get("min", 0.0))
        self._max = float(config.get("max", 1.0))
        self._curve = config.get("curve", "linear")

    def execute(self, event: "MidiEvent") -> None:
        """Normalize CC value, apply curve, scale, and send via OSC."""
        if event.type != "cc":
            return

        try:
            normalized = event.value / 127.0
            curved = _apply_curve(normalized, self._curve)
            scaled = _scale_to_range(curved, self._min, self._max)

            sender = OscSender(self._host, self._port)
            if self._param:
                sender.send(self._address, self._param, float(scaled))
            else:
                sender.send(self._address, float(scaled))

            logger.debug(
                "OSC %s %s=%.3f (midi=%d, curve=%s)",
                self._address, self._param, scaled,
                event.value, self._curve,
            )
        except Exception as e:
            logger.error("OscSendAction error: %s", e)


class OscSendRelativeAction(Action):
    """Forward CC relative values (encoders) to Pd via OSC.

    Accumulates two's complement deltas and clips to [min, max].
    Uses class-level accumulators that persist across action instances
    (same pattern as HotkeyAction._toggle_states).

    Config:
        osc_host: Target host (default: "127.0.0.1")
        osc_port: Target UDP port (default: 9000)
        osc_address: OSC address pattern (default: "/pd/param")
        osc_param: Parameter bus name
        min: Minimum accumulated value (default: 0.0)
        max: Maximum accumulated value (default: 127.0)
        step: Delta per encoder tick (default: 1.0)
        initial: Starting value (default: midpoint of min/max)
    """

    _accumulators: dict[str, float] = {}
    _acc_lock = threading.Lock()

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._host = config.get("osc_host", "127.0.0.1")
        self._port = config.get("osc_port", 9000)
        self._address = config.get("osc_address", "/pd/param")
        self._param = config.get("osc_param", "")
        self._min = float(config.get("min", 0.0))
        self._max = float(config.get("max", 127.0))
        self._step = float(config.get("step", 1.0))

        default_initial = (self._min + self._max) / 2.0
        self._initial = float(config.get("initial", default_initial))

        self._acc_key = self._param or f"{self._address}_{self._port}"

    def execute(self, event: "MidiEvent") -> None:
        """Accumulate encoder delta and send via OSC."""
        if event.type != "cc":
            return

        try:
            # Decode two's complement: 1-63 = CW, 65-127 = CCW
            value = event.value
            if 1 <= value <= 63:
                delta = value * self._step
            elif 65 <= value <= 127:
                delta = (value - 128) * self._step
            else:
                return  # 0 or 64 — ignore

            with self._acc_lock:
                if self._acc_key not in self._accumulators:
                    self._accumulators[self._acc_key] = self._initial
                current = self._accumulators[self._acc_key]
                new_value = max(self._min, min(self._max, current + delta))
                self._accumulators[self._acc_key] = new_value

            sender = OscSender(self._host, self._port)
            if self._param:
                sender.send(self._address, self._param, float(new_value))
            else:
                sender.send(self._address, float(new_value))

            logger.debug(
                "OSC relative %s %s=%.2f (delta=%.1f)",
                self._address, self._param, new_value, delta,
            )
        except Exception as e:
            logger.error("OscSendRelativeAction error: %s", e)

    @classmethod
    def reset_accumulators(cls) -> None:
        """Reset all accumulators (for profile switch or testing)."""
        with cls._acc_lock:
            cls._accumulators.clear()


class OscSendTriggerAction(Action):
    """Forward button presses to Pd via OSC (bang or toggle).

    Config:
        osc_host: Target host (default: "127.0.0.1")
        osc_port: Target UDP port (default: 9000)
        osc_address: OSC address pattern (default: "/pd/param")
        osc_param: Parameter bus name
        mode: "bang" (sends 1.0 on press) or "toggle" (alternates 0.0/1.0)
    """

    _toggle_states: dict[str, bool] = {}

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._host = config.get("osc_host", "127.0.0.1")
        self._port = config.get("osc_port", 9000)
        self._address = config.get("osc_address", "/pd/param")
        self._param = config.get("osc_param", "")
        self._mode = config.get("mode", "bang")

        self._toggle_key = self._param or f"{self._address}_{self._port}"

    def execute(self, event: "MidiEvent") -> None:
        """Send bang or toggle via OSC on button press."""
        if event.type != "note_on" or event.value == 0:
            return

        try:
            sender = OscSender(self._host, self._port)

            if self._mode == "toggle":
                current = self._toggle_states.get(self._toggle_key, False)
                new_state = not current
                self._toggle_states[self._toggle_key] = new_state
                send_value = 1.0 if new_state else 0.0
            else:
                send_value = 1.0

            if self._param:
                sender.send(self._address, self._param, float(send_value))
            else:
                sender.send(self._address, float(send_value))

            logger.debug(
                "OSC trigger %s %s=%.1f (mode=%s)",
                self._address, self._param, send_value, self._mode,
            )
        except Exception as e:
            logger.error("OscSendTriggerAction error: %s", e)

    @classmethod
    def reset_toggle_states(cls) -> None:
        """Reset all toggle states (for profile switch or testing)."""
        cls._toggle_states.clear()
