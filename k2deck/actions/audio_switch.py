"""Audio Switch Action - Change default audio output/input device.

Allows cycling through configured audio devices with a button press.
"""

import logging
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.core.audio_devices import (
    cycle_audio_devices,
    get_audio_devices,
    set_default_audio_device_by_name,
)

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


class AudioSwitchAction(Action):
    """Switch between audio devices.

    Config options:
        devices: List of device name patterns to cycle through (required)
        type: "output" (speakers) or "input" (microphones), default "output"

    Config example (cycle between devices):
    {
        "action": "audio_switch",
        "devices": ["Speakers", "Headphones"],
        "type": "output"
    }

    Config example (switch to specific device):
    {
        "action": "audio_switch",
        "devices": ["Headphones"],
        "type": "output"
    }
    """

    def __init__(self, config: dict):
        """Initialize audio switch action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._devices = config.get("devices", [])
        self._device_type = config.get("type", "output")

    def execute(self, event: "MidiEvent") -> None:
        """Switch audio device.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        if not self._devices:
            logger.warning("AudioSwitchAction: no devices configured")
            return

        if len(self._devices) == 1:
            # Single device - just switch to it
            device = self._devices[0]
            if set_default_audio_device_by_name(device, self._device_type):
                logger.info("Switched to: %s", device)
            else:
                logger.warning("Failed to switch to: %s", device)
        else:
            # Multiple devices - cycle through them
            result = cycle_audio_devices(self._devices, self._device_type)
            if result:
                logger.info("Audio device cycled to: %s", result)
            else:
                logger.warning("Failed to cycle audio devices")


class AudioListAction(Action):
    """List available audio devices (for debugging/discovery).

    Logs all available audio devices. Useful for finding device names
    to use in AudioSwitchAction configuration.

    Config example:
    {
        "action": "audio_list",
        "type": "output"
    }
    """

    def __init__(self, config: dict):
        """Initialize audio list action.

        Args:
            config: Action configuration.
        """
        super().__init__(config)
        self._device_type = config.get("type", "output")

    def execute(self, event: "MidiEvent") -> None:
        """List audio devices.

        Args:
            event: The MIDI event that triggered this action.
        """
        # Only trigger on note_on with velocity > 0
        if event.type != "note_on" or event.value == 0:
            return

        devices = get_audio_devices(self._device_type)

        logger.info("=== Audio Devices (%s) ===", self._device_type)
        for device in devices:
            default_marker = " [DEFAULT]" if device.is_default else ""
            logger.info("  %s%s", device.name, default_marker)
            logger.debug("    ID: %s", device.id)
        logger.info("=== End of list (%d devices) ===", len(devices))
