"""Tests for layer management."""

from k2deck.core import layers
from k2deck.core.midi_listener import MidiEvent


class TestLayers:
    """Tests for layer management."""

    def setup_method(self):
        """Reset layer state before each test."""
        layers.reset()

    def test_default_layer_is_1(self):
        """Should start on layer 1."""
        assert layers.get_current_layer() == 1

    def test_set_valid_layer(self):
        """Should set layer when valid."""
        assert layers.set_layer(2) is True
        assert layers.get_current_layer() == 2

    def test_set_invalid_layer_too_high(self):
        """Should reject layer above count."""
        assert layers.set_layer(4) is False
        assert layers.get_current_layer() == 1

    def test_set_invalid_layer_zero(self):
        """Should reject layer 0."""
        assert layers.set_layer(0) is False
        assert layers.get_current_layer() == 1

    def test_set_same_layer_returns_false(self):
        """Should return False when setting same layer."""
        assert layers.set_layer(1) is False  # Already on layer 1

    def test_cycle_layer(self):
        """Should cycle through layers."""
        assert layers.get_current_layer() == 1
        layers.cycle_layer()
        assert layers.get_current_layer() == 2
        layers.cycle_layer()
        assert layers.get_current_layer() == 3
        layers.cycle_layer()
        assert layers.get_current_layer() == 1  # Wrap around

    def test_layer_callback(self):
        """Should call callback on layer change."""
        callback_results = []

        def callback(layer: int):
            callback_results.append(layer)

        layers.register_layer_change_callback(callback)
        layers.set_layer(2)
        layers.set_layer(3)

        assert callback_results == [2, 3]

        layers.unregister_layer_change_callback(callback)

    def test_resolve_simple_mapping(self):
        """Should return simple mapping for all layers."""
        mapping = {
            "name": "Test Button",
            "action": "hotkey",
            "keys": ["f1"],
        }

        result = layers.resolve_layer_mapping(mapping, 36)
        assert result == mapping

    def test_resolve_layer_specific_mapping(self):
        """Should return layer-specific mapping."""
        mapping = {
            "name": "Test Button",
            "layer_1": {"action": "hotkey", "keys": ["f1"]},
            "layer_2": {"action": "hotkey", "keys": ["f2"]},
            "layer_3": {"action": "spotify_play_pause"},
            "led": {"color": "green"},
        }

        # Layer 1
        result = layers.resolve_layer_mapping(mapping, 36)
        assert result["action"] == "hotkey"
        assert result["keys"] == ["f1"]
        assert result["name"] == "Test Button"
        assert result["led"] == {"color": "green"}

        # Layer 2
        layers.set_layer(2)
        result = layers.resolve_layer_mapping(mapping, 36)
        assert result["action"] == "hotkey"
        assert result["keys"] == ["f2"]

        # Layer 3
        layers.set_layer(3)
        result = layers.resolve_layer_mapping(mapping, 36)
        assert result["action"] == "spotify_play_pause"

    def test_resolve_missing_layer_returns_none(self):
        """Should return None if layer not defined."""
        mapping = {
            "name": "Test Button",
            "layer_1": {"action": "hotkey", "keys": ["f1"]},
            # No layer_2 or layer_3
        }

        layers.set_layer(2)
        result = layers.resolve_layer_mapping(mapping, 36)
        assert result is None

    def test_handle_layer_button(self):
        """Should handle layer button press."""
        event = MidiEvent(
            type="note_on",
            channel=16,
            note=15,  # Layer button
            cc=None,
            value=127,
            timestamp=0.0,
        )

        assert layers.get_current_layer() == 1
        assert layers.handle_layer_button(event) is True
        assert layers.get_current_layer() == 2

    def test_handle_non_layer_button(self):
        """Should not handle non-layer button."""
        event = MidiEvent(
            type="note_on",
            channel=16,
            note=36,  # Not layer button
            cc=None,
            value=127,
            timestamp=0.0,
        )

        result = layers.handle_layer_button(event)
        assert result is False

    def test_layer_led_colors(self):
        """Should return correct LED colors for layers."""
        assert layers.get_layer_led_color(1) == "green"
        assert layers.get_layer_led_color(2) == "amber"
        assert layers.get_layer_led_color(3) == "red"
