"""Mapping Engine - Resolves MIDI events to actions.

Loads JSON config and maps MIDI events to their configured actions.
Supports software layers for the Xone:K2's multi-layer functionality.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from k2deck.actions.audio_switch import AudioListAction, AudioSwitchAction
from k2deck.actions.base import Action
from k2deck.actions.conditional import ConditionalAction
from k2deck.actions.counter import CounterAction
from k2deck.actions.folder import FolderAction, FolderBackAction, FolderRootAction
from k2deck.actions.obs import (
    OBSMuteAction,
    OBSRecordAction,
    OBSSceneAction,
    OBSSourceToggleAction,
    OBSStreamAction,
)
from k2deck.actions.hotkey import HotkeyAction, HotkeyRelativeAction
from k2deck.actions.mouse_scroll import MouseScrollAction
from k2deck.actions.multi import MultiAction, MultiToggleAction
from k2deck.actions.spotify import (
    SpotifyLikeAction,
    SpotifyNextAction,
    SpotifyPlayPauseAction,
    SpotifyPreviousAction,
    SpotifyPrevNextAction,
    SpotifyRepeatAction,
    SpotifySeekAction,
    SpotifyShuffleAction,
    SpotifyVolumeAction,
)
from k2deck.actions.sound import SoundPlayAction, SoundStopAction
from k2deck.actions.system import ClipboardPasteAction, NoopAction, OpenURLAction, SystemAction
from k2deck.actions.tts import TTSAction
from k2deck.actions.twitch import (
    TwitchChatAction,
    TwitchClipAction,
    TwitchGameAction,
    TwitchMarkerAction,
    TwitchTitleAction,
)
from k2deck.actions.osc_send import OscSendAction, OscSendRelativeAction, OscSendTriggerAction
from k2deck.actions.volume import VolumeAction
from k2deck.actions.window import FocusAction, LaunchAction
from k2deck.core import folders, layers

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
    "open_url": OpenURLAction,
    "clipboard_paste": ClipboardPasteAction,
    "multi": MultiAction,
    "multi_toggle": MultiToggleAction,
    "conditional": ConditionalAction,
    "focus": FocusAction,
    "launch": LaunchAction,
    # Sound actions
    "sound_play": SoundPlayAction,
    "sound_stop": SoundStopAction,
    # Audio device actions
    "audio_switch": AudioSwitchAction,
    "audio_list": AudioListAction,
    # OBS WebSocket actions
    "obs_scene": OBSSceneAction,
    "obs_source_toggle": OBSSourceToggleAction,
    "obs_stream": OBSStreamAction,
    "obs_record": OBSRecordAction,
    "obs_mute": OBSMuteAction,
    # Counter action
    "counter": CounterAction,
    # Text-to-Speech action
    "tts": TTSAction,
    # Folder actions
    "folder": FolderAction,
    "folder_back": FolderBackAction,
    "folder_root": FolderRootAction,
    # Spotify API actions
    "spotify_play_pause": SpotifyPlayPauseAction,
    "spotify_next": SpotifyNextAction,
    "spotify_previous": SpotifyPreviousAction,
    "spotify_like": SpotifyLikeAction,
    "spotify_shuffle": SpotifyShuffleAction,
    "spotify_repeat": SpotifyRepeatAction,
    "spotify_volume": SpotifyVolumeAction,
    "spotify_seek": SpotifySeekAction,
    "spotify_prev_next": SpotifyPrevNextAction,
    # Twitch API actions
    "twitch_marker": TwitchMarkerAction,
    "twitch_clip": TwitchClipAction,
    "twitch_chat": TwitchChatAction,
    "twitch_title": TwitchTitleAction,
    "twitch_game": TwitchGameAction,
    # OSC send actions (Pure Data bridge)
    "osc_send": OscSendAction,
    "osc_send_relative": OscSendRelativeAction,
    "osc_send_trigger": OscSendTriggerAction,
}


class ConfigValidationError(Exception):
    """Raised when config validation fails."""

    pass


class MappingEngine:
    """Resolves MIDI events to configured actions.

    Supports multiple K2 controllers via zones. Each zone has its own
    MIDI channel and mappings, allowing two K2s to work as one extended
    controller.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize mapping engine.

        Args:
            config_path: Path to JSON config file. If None, must call load_config later.
        """
        self._config: dict = {}
        self._midi_channels: list[int] = [16]  # Support multiple channels
        self._mappings: dict = {}
        self._zones: dict[int, dict] = {}  # Channel -> zone mappings
        self._led_offsets: dict[str, int] = {"red": 0, "amber": 36, "green": 72}

        if config_path:
            self.load_config(config_path)

    @property
    def config(self) -> dict:
        """Get raw config dict."""
        return self._config

    @property
    def midi_channel(self) -> int:
        """Get primary MIDI channel (1-16). For backward compatibility."""
        return self._midi_channels[0] if self._midi_channels else 16

    @property
    def midi_channels(self) -> list[int]:
        """Get all configured MIDI channels."""
        return self._midi_channels.copy()

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
        self._led_offsets = self._config.get(
            "led_color_offsets",
            {"red": 0, "amber": 36, "green": 72},
        )

        # Handle zones (multi-K2) or single channel config
        if "zones" in self._config:
            self._load_zones()
        else:
            # Legacy single-channel config
            channel = self._config.get("midi_channel", 16)
            self._midi_channels = [channel]
            self._mappings = self._config.get("mappings", {})
            self._zones = {channel: self._mappings}

        logger.info(
            "Loaded config: %s (channels %s, %d mappings)",
            self._config.get("profile_name", "unknown"),
            self._midi_channels,
            self._count_mappings(),
        )

    def _load_zones(self) -> None:
        """Load multi-K2 zone configuration."""
        zones_config = self._config.get("zones", {})
        self._midi_channels = []
        self._zones = {}

        for zone_name, zone_data in zones_config.items():
            if zone_name.startswith("_"):
                continue  # Skip comments

            channel = zone_data.get("channel")
            if channel is None:
                logger.warning("Zone '%s' missing channel, skipping", zone_name)
                continue

            if not isinstance(channel, int) or not 1 <= channel <= 16:
                logger.warning("Zone '%s' invalid channel %s, skipping", zone_name, channel)
                continue

            self._midi_channels.append(channel)
            self._zones[channel] = zone_data.get("mappings", {})

            logger.info("  Zone '%s': channel %d, %d mappings",
                        zone_name, channel, self._count_zone_mappings(self._zones[channel]))

        # Also set default mappings for backward compatibility
        if self._zones:
            first_channel = self._midi_channels[0]
            self._mappings = self._zones[first_channel]

    def _count_zone_mappings(self, zone_mappings: dict) -> int:
        """Count mappings in a zone."""
        count = 0
        for section in ["note_on", "cc_absolute", "cc_relative"]:
            if section in zone_mappings:
                count += sum(1 for k in zone_mappings[section] if not k.startswith("_"))
        return count

    def _validate_config(self) -> None:
        """Validate config structure."""
        # Required: midi_channel
        if "midi_channel" in self._config:
            channel = self._config["midi_channel"]
            if not isinstance(channel, int) or not 1 <= channel <= 16:
                raise ConfigValidationError(
                    f"midi_channel must be int 1-16, got: {channel}"
                )

        # Required: mappings OR zones
        if "mappings" not in self._config and "zones" not in self._config:
            raise ConfigValidationError("Config missing 'mappings' or 'zones' section")

        # Validate zones OR mappings
        if "zones" in self._config:
            zones = self._config["zones"]
            if not isinstance(zones, dict):
                raise ConfigValidationError("'zones' must be a dict")

            for zone_name, zone_data in zones.items():
                if zone_name.startswith("_"):
                    continue
                if not isinstance(zone_data, dict):
                    raise ConfigValidationError(f"Zone '{zone_name}' must be a dict")
                if "mappings" in zone_data:
                    mappings = zone_data["mappings"]
                    for section in ["note_on", "cc_absolute", "cc_relative"]:
                        if section in mappings:
                            self._validate_mapping_section(f"{zone_name}.{section}", mappings[section])
        else:
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

        Supports:
        - Multiple K2 controllers via zones (different channels)
        - Layer-specific mappings (layer_1, layer_2, layer_3)

        Args:
            event: The MIDI event to resolve.

        Returns:
            Tuple of (Action instance, mapping config) or (None, None) if unmapped.
        """
        # Check if channel is in our configured channels
        if event.channel not in self._midi_channels:
            return None, None

        # Get zone mappings for this channel
        zone_mappings = self._zones.get(event.channel, self._mappings)

        # Handle layer button specially
        if event.type == "note_on" and layers.is_layer_button(event.note):
            if layers.handle_layer_button(event):
                # Layer button consumed the event
                return None, None

        mapping_config = None

        if event.type == "note_on":
            # Check if we're in a folder (folders only affect note_on mappings)
            folder_mgr = folders.get_folder_manager()
            if folder_mgr.in_folder:
                # Look in folder mappings first
                folder_mappings = self._config.get("folders", {}).get(
                    folder_mgr.current_folder, {}
                )
                folder_note_mappings = folder_mappings.get("note_on", {})
                raw_config = folder_note_mappings.get(str(event.note))
                if raw_config:
                    # Resolve layer-specific mapping from folder
                    mapping_config = layers.resolve_layer_mapping(raw_config, event.note)

            # If not found in folder (or not in folder), use regular mappings
            if mapping_config is None:
                note_mappings = zone_mappings.get("note_on", {})
                raw_config = note_mappings.get(str(event.note))
                # Resolve layer-specific mapping
                mapping_config = layers.resolve_layer_mapping(raw_config, event.note)

        elif event.type == "note_off":
            # Note off typically doesn't trigger actions
            return None, None

        elif event.type == "cc":
            # Determine if relative or absolute based on value
            # Two's complement: 1-63 or 65-127 suggests relative encoder
            # Values across full 0-127 range suggest absolute fader/knob
            value = event.value

            # First check cc_relative (for encoders)
            relative_mappings = zone_mappings.get("cc_relative", {})
            if str(event.cc) in relative_mappings:
                # Check if value looks like relative (1, 127, or similar)
                if value in (1, 127) or (1 <= value <= 63) or (65 <= value <= 127):
                    raw_config = relative_mappings.get(str(event.cc))
                    mapping_config = layers.resolve_layer_mapping(raw_config, event.cc)

            # If not found in relative, check absolute
            if mapping_config is None:
                absolute_mappings = zone_mappings.get("cc_absolute", {})
                raw_config = absolute_mappings.get(str(event.cc))
                mapping_config = layers.resolve_layer_mapping(raw_config, event.cc)

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
