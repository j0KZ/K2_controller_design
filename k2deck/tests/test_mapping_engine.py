"""Tests for the mapping engine."""

import json
import tempfile
from pathlib import Path

import pytest

from k2deck.core.mapping_engine import ConfigValidationError, MappingEngine
from k2deck.core.midi_listener import MidiEvent


def create_temp_config(config_dict: dict) -> Path:
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
    ) as f:
        json.dump(config_dict, f)
        return Path(f.name)


class TestMappingEngine:
    """Tests for MappingEngine."""

    def test_load_valid_config(self):
        """Should load a valid config file."""
        config = {
            "profile_name": "test",
            "midi_channel": 16,
            "mappings": {
                "note_on": {
                    "36": {
                        "name": "Test Button",
                        "action": "hotkey",
                        "keys": ["a"],
                    }
                }
            },
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            assert engine.midi_channel == 16
            assert "note_on" in engine._mappings
        finally:
            path.unlink()

    def test_missing_mappings_raises(self):
        """Should raise for config without mappings."""
        config = {"midi_channel": 16}
        path = create_temp_config(config)
        try:
            with pytest.raises(ConfigValidationError, match="missing 'mappings'"):
                MappingEngine(path)
        finally:
            path.unlink()

    def test_invalid_channel_raises(self):
        """Should raise for invalid MIDI channel."""
        config = {
            "midi_channel": 17,  # Invalid
            "mappings": {"note_on": {}},
        }
        path = create_temp_config(config)
        try:
            with pytest.raises(ConfigValidationError, match="midi_channel"):
                MappingEngine(path)
        finally:
            path.unlink()

    def test_resolve_note_on(self):
        """Should resolve note_on events."""
        config = {
            "midi_channel": 16,
            "mappings": {
                "note_on": {
                    "36": {
                        "name": "Test",
                        "action": "hotkey",
                        "keys": ["space"],
                    }
                }
            },
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            event = MidiEvent(
                type="note_on",
                channel=16,
                note=36,
                cc=None,
                value=127,
                timestamp=0.0,
            )
            action, mapping = engine.resolve(event)
            assert action is not None
            assert action.name == "Test"
        finally:
            path.unlink()

    def test_resolve_unmapped_returns_none(self):
        """Should return None for unmapped controls."""
        config = {
            "midi_channel": 16,
            "mappings": {"note_on": {}},
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            event = MidiEvent(
                type="note_on",
                channel=16,
                note=99,  # Not mapped
                cc=None,
                value=127,
                timestamp=0.0,
            )
            action, mapping = engine.resolve(event)
            assert action is None
            assert mapping is None
        finally:
            path.unlink()

    def test_resolve_wrong_channel_returns_none(self):
        """Should return None for events on wrong channel."""
        config = {
            "midi_channel": 16,
            "mappings": {
                "note_on": {
                    "36": {"name": "Test", "action": "hotkey", "keys": ["a"]}
                }
            },
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            event = MidiEvent(
                type="note_on",
                channel=15,  # Wrong channel
                note=36,
                cc=None,
                value=127,
                timestamp=0.0,
            )
            action, mapping = engine.resolve(event)
            assert action is None
        finally:
            path.unlink()

    def test_resolve_cc_absolute(self):
        """Should resolve cc_absolute events."""
        config = {
            "midi_channel": 16,
            "mappings": {
                "cc_absolute": {
                    "1": {
                        "name": "Volume",
                        "action": "volume",
                        "target_process": "__master__",
                    }
                }
            },
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            event = MidiEvent(
                type="cc",
                channel=16,
                note=None,
                cc=1,
                value=64,
                timestamp=0.0,
            )
            action, mapping = engine.resolve(event)
            assert action is not None
            assert action.name == "Volume"
        finally:
            path.unlink()

    def test_resolve_cc_relative(self):
        """Should resolve cc_relative events (encoders)."""
        config = {
            "midi_channel": 16,
            "mappings": {
                "cc_relative": {
                    "16": {
                        "name": "Scroll",
                        "action": "mouse_scroll",
                        "step": 3,
                    }
                }
            },
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            # CW value
            event = MidiEvent(
                type="cc",
                channel=16,
                note=None,
                cc=16,
                value=1,  # CW
                timestamp=0.0,
            )
            action, mapping = engine.resolve(event)
            assert action is not None
            assert action.name == "Scroll"
        finally:
            path.unlink()

    def test_get_all_button_notes(self):
        """Should return all configured button notes."""
        config = {
            "midi_channel": 16,
            "mappings": {
                "note_on": {
                    "36": {"name": "A", "action": "noop"},
                    "37": {"name": "B", "action": "noop"},
                    "40": {"name": "C", "action": "noop"},
                }
            },
        }
        path = create_temp_config(config)
        try:
            engine = MappingEngine(path)
            notes = engine.get_all_button_notes()
            assert sorted(notes) == [36, 37, 40]
        finally:
            path.unlink()
