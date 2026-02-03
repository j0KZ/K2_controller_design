"""Tests for LED color utilities."""

import pytest

from k2deck.feedback.led_colors import (
    COLOR_OFFSET_AMBER,
    COLOR_OFFSET_GREEN,
    COLOR_OFFSET_RED,
    base_note_from_led,
    get_all_led_notes,
    led_note,
)


class TestLedColors:
    """Tests for LED color functions."""

    def test_color_offsets(self):
        """Verify color offset constants."""
        assert COLOR_OFFSET_RED == 0
        assert COLOR_OFFSET_AMBER == 36
        assert COLOR_OFFSET_GREEN == 72

    def test_led_note_red(self):
        """led_note should return base + 0 for red."""
        assert led_note(36, "red") == 36
        assert led_note(0, "red") == 0
        assert led_note(48, "red") == 48

    def test_led_note_amber(self):
        """led_note should return base + 36 for amber."""
        assert led_note(36, "amber") == 72
        assert led_note(0, "amber") == 36
        assert led_note(48, "amber") == 84

    def test_led_note_green(self):
        """led_note should return base + 72 for green."""
        assert led_note(36, "green") == 108
        assert led_note(0, "green") == 72
        assert led_note(48, "green") == 120

    def test_led_note_invalid_color(self):
        """led_note should raise for invalid colors."""
        with pytest.raises(ValueError, match="Invalid color"):
            led_note(36, "blue")
        with pytest.raises(ValueError, match="Invalid color"):
            led_note(36, "off")

    def test_base_note_from_led_red(self):
        """base_note_from_led should identify red notes (0-35 range)."""
        # Notes 0-35 are in the red range
        base, color = base_note_from_led(24)
        assert base == 24
        assert color == "red"

    def test_base_note_from_led_amber(self):
        """base_note_from_led should identify amber notes (36-71 range)."""
        # Note 60 is in amber range: 60 - 36 = base 24
        base, color = base_note_from_led(60)
        assert base == 24
        assert color == "amber"

    def test_base_note_from_led_green(self):
        """base_note_from_led should identify green notes (72+ range)."""
        # Note 96 is in green range: 96 - 72 = base 24
        base, color = base_note_from_led(96)
        assert base == 24
        assert color == "green"

    def test_get_all_led_notes(self):
        """get_all_led_notes should return all three notes."""
        notes = get_all_led_notes(36)
        assert notes == {"red": 36, "amber": 72, "green": 108}

    def test_get_all_led_notes_zero(self):
        """get_all_led_notes should work with base note 0."""
        notes = get_all_led_notes(0)
        assert notes == {"red": 0, "amber": 36, "green": 72}
