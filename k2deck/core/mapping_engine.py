"""Mapping Engine - Resolves MIDI events to actions.

Loads JSON config and maps MIDI events to their configured actions.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from k2deck.actions.base import Action
from k2deck.actions.hotkey import HotkeyAction, HotkeyRelativeAction
from k2deck.actions.mouse_scroll import MouseScrollAction
from k2deck.actions.system import NoopAction, SystemAction
from k2deck.actions.volume import VolumeAction

if TYPE_CHECKING:
    from k2deck.core.midi_listener import MidiEvent

logger = logging.getLogger(__name__)


# Action type registry
ACTION_TYPES: dict[str, type[Action]] = {
    "hotkey": HotkeyAction,
    "hotkey_relative": HotkeyRelativeAction,
    "mouse_scroll": MouseScrollAction,
    "volume": VolumeAction,
    "media_key": HotkeyAction,  # Media keys are just special hotkeys
    "system": SystemAction,
    "noop": NoopAction,
}


class ConfigValidationError(Exception):
    """Raised when config validation fails."""

    pass


class MappingEngine:
    """Resolves MIDI events to configured actions."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize mapping engine.

        Args:
            config_path: Path to JSON config file. If None, must call load_config later.
        """
        self._config: dict = {}
        self._midi_channel: int = 16
        self._mappings: dict = {}
        self._led_offsets: dict[str, int] = {"red": 0, "amber": 36, "green": 72}

        if config_path:
            self.load_config(config_path)

    @property
    def config(self) -> dict:
        """Get raw config dict."""
        return self._config

    @property
    def midi_channel(self) -> int:
        """Get configured MIDI channel (1-16)."""
        return self._midi_channel

    @property
    def led_color_offsets(self) -> dict[str, int]:
        """Get LED color offsets."""
        return self._led_offsets

    def load_config(self, config_path: str | Path) -> None:
        """Load and validate config from JSON file.

        Args:
            config_path: Path to JSON config file.

        Raises:
            ConfigValidationError: If config is invalid.
            FileNotFoundError: If config file doesn't exist.
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                self._config = json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigValidationError(f"Invalid JSON: {e}")

        self._validate_config()
        self._midi_channel = self._config.get("midi_channel", 16)
        self._mappings = self._config.get("mappings", {})
        self._led_offsets = self._config.get(
            "led_color_offsets",
            {"red": 0, "amber": 36, "green": 72},
        )

        logger.info(
            "Loaded config: %s (channel %d, %d mappings)",
            self._config.get("profile_name", "unknown"),
            self._midi_channel,
            self._count_mappings(),
        )

    def _validate_config(self) -> None:
        """Validate config structure."""
        # Required: midi_channel
        if "midi_channel" in self._config:
            channel = self._config["midi_channel"]
            if not isinstance(channel, int) or not 1 <= channel <= 16:
                raise ConfigValidationError(
                    f"midi_channel must be int 1-16, got: {channel}"
                )

        # Required: mappings
        if "mappings" not in self._config:
            raise ConfigValidationError("Config missing 'mappings' section")

        mappings = self._config["mappings"]
        if not isinstance(mappings, dict):
            raise ConfigValidationError("'mappings' must be a dict")

        # Validate each mapping entry
        for section in ["note_on", "cc_absolute", "cc_relative"]:
            if section in mappings:
                self._validate_mapping_section(section, mappings[section])

    def _validate_mapping_section(self, section: str, entries: dict) -> None:
        """Validate a mapping section."""
        if not isinstance(entries, dict):
            raise ConfigValidationError(f"'{section}' must be a dict")

        for key, entry in entries.items():
            # Skip metadata keys (start with _)
            if key.startswith("_"):
                continue

            if not isinstance(entry, dict):
                raise ConfigValidationError(
                    f"Mapping {section}[{key}] must be a dict"
                )

            # name is optional but recommended
            # action is required
            if "action" not in entry:
                raise ConfigValidationError(
                    f"Mapping {section}[{key}] missing 'action'"
                )

            action_type = entry["action"]
            if action_type not in ACTION_TYPES:
                logger.warning(
                    "Unknown action type '%s' in %s[%s], will skip",
                    action_type,
                    section,
                    key,
                )

    def _count_mappings(self) -> int:
        """Count total number of mappings (excluding metadata keys)."""
        count = 0
        for section in ["note_on", "cc_absolute", "cc_relative"]:
            if section in self._mappings:
                count += sum(1 for k in self._mappings[section] if not k.startswith("_"))
        return count

    def resolve(self, event: "MidiEvent") -> tuple[Action | None, dict | None]:
        """Resolve MIDI event to action.

        Args:
            event: The MIDI event to resolve.

        Returns:
            Tuple of (Action instance, mapping config) or (None, None) if unmapped.
        """
        # Check channel
        if event.channel != self._midi_channel:
            return None, None

        mapping_config = None

        if event.type == "note_on":
            # Look up in note_on mappings
            note_mappings = self._mappings.get("note_on", {})
            mapping_config = note_mappings.get(str(event.note))

        elif event.type == "note_off":
            # Note off typically doesn't trigger actions
            return None, None

        elif event.type == "cc":
            # Determine if relative or absolute based on value
            # Two's complement: 1-63 or 65-127 suggests relative encoder
            # Values across full 0-127 range suggest absolute fader/knob
            value = event.value

            # First check cc_relative (for encoders)
            relative_mappings = self._mappings.get("cc_relative", {})
            if str(event.cc) in relative_mappings:
                # Check if value looks like relative (1, 127, or similar)
                if value in (1, 127) or (1 <= value <= 63) or (65 <= value <= 127):
                    mapping_config = relative_mappings.get(str(event.cc))

            # If not found in relative, check absolute
            if mapping_config is None:
                absolute_mappings = self._mappings.get("cc_absolute", {})
                mapping_config = absolute_mappings.get(str(event.cc))

        if mapping_config is None:
            return None, None

        # Create action instance
        action_type = mapping_config.get("action")
        if action_type not in ACTION_TYPES:
            logger.debug("Unknown action type: %s", action_type)
            return None, None

        action_class = ACTION_TYPES[action_type]
        return action_class(mapping_config), mapping_config

    def reload(self) -> None:
        """Reload config from file.

        Note: Requires config_path to be stored. For hot-reload use
        ProfileManager instead.
        """
        logger.info("Config reload requested (not implemented in MappingEngine)")

    def get_led_config(self, base_note: int) -> dict | None:
        """Get LED config for a button.

        Args:
            base_note: Button's base MIDI note.

        Returns:
            LED config dict or None.
        """
        note_mappings = self._mappings.get("note_on", {})
        mapping = note_mappings.get(str(base_note))
        if mapping:
            return mapping.get("led")
        return None

    def get_all_button_notes(self) -> list[int]:
        """Get all configured button note numbers.

        Returns:
            List of base note numbers.
        """
        note_mappings = self._mappings.get("note_on", {})
        return [int(note) for note in note_mappings.keys() if not note.startswith("_")]
