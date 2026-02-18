"""Tests for keyboard.py - Windows SendInput simulation."""

from unittest.mock import patch

from k2deck.core import keyboard


class TestScanCodes:
    """Test scan code mappings."""

    def test_letters_exist(self):
        """All lowercase letters should have scan codes."""
        for char in "abcdefghijklmnopqrstuvwxyz":
            assert char in keyboard.SCAN_CODES, f"Missing scan code for '{char}'"
            scan, extended = keyboard.SCAN_CODES[char]
            assert isinstance(scan, int)
            assert isinstance(extended, bool)

    def test_numbers_exist(self):
        """All digits should have scan codes."""
        for digit in "0123456789":
            assert digit in keyboard.SCAN_CODES, f"Missing scan code for '{digit}'"

    def test_function_keys_exist(self):
        """F1-F12 should have scan codes."""
        for i in range(1, 13):
            key = f"f{i}"
            assert key in keyboard.SCAN_CODES, f"Missing scan code for '{key}'"

    def test_modifiers_exist(self):
        """Common modifiers should have scan codes."""
        modifiers = ["ctrl", "alt", "shift", "win", "cmd"]
        for mod in modifiers:
            assert mod in keyboard.SCAN_CODES, f"Missing scan code for '{mod}'"

    def test_media_keys_in_vk_codes(self):
        """Media keys should have VK codes."""
        media_keys = [
            "media_play_pause",
            "media_next",
            "media_previous",
            "volume_up",
            "volume_down",
        ]
        for key in media_keys:
            assert key in keyboard.MEDIA_VK_CODES, f"Missing VK code for '{key}'"

    def test_extended_keys_marked(self):
        """Arrow keys and navigation should be marked as extended."""
        extended_keys = [
            "up",
            "down",
            "left",
            "right",
            "insert",
            "delete",
            "home",
            "end",
        ]
        for key in extended_keys:
            _, is_extended = keyboard.SCAN_CODES[key]
            assert is_extended, f"'{key}' should be marked as extended"


class TestInputCreation:
    """Test INPUT structure creation."""

    def test_create_key_input_press(self):
        """Key press should have correct flags."""
        inp = keyboard._create_key_input(0x1E, extended=False, key_up=False)
        assert inp.type == keyboard.INPUT_KEYBOARD
        assert inp.union.ki.wScan == 0x1E
        assert inp.union.ki.dwFlags == keyboard.KEYEVENTF_SCANCODE

    def test_create_key_input_release(self):
        """Key release should have KEYUP flag."""
        inp = keyboard._create_key_input(0x1E, extended=False, key_up=True)
        expected_flags = keyboard.KEYEVENTF_SCANCODE | keyboard.KEYEVENTF_KEYUP
        assert inp.union.ki.dwFlags == expected_flags

    def test_create_key_input_extended(self):
        """Extended key should have EXTENDEDKEY flag."""
        inp = keyboard._create_key_input(0x48, extended=True, key_up=False)
        expected_flags = keyboard.KEYEVENTF_SCANCODE | keyboard.KEYEVENTF_EXTENDEDKEY
        assert inp.union.ki.dwFlags == expected_flags

    def test_create_vk_input_press(self):
        """VK input for media keys should use vk_code not scan."""
        inp = keyboard._create_vk_input(keyboard.VK_MEDIA_PLAY_PAUSE, key_up=False)
        assert inp.type == keyboard.INPUT_KEYBOARD
        assert inp.union.ki.wVk == keyboard.VK_MEDIA_PLAY_PAUSE
        assert inp.union.ki.wScan == 0
        assert inp.union.ki.dwFlags == 0


class TestKeyPressRelease:
    """Test press_key and release_key functions."""

    @patch.object(keyboard, "_send_input")
    def test_press_key_valid(self, mock_send):
        """Valid key press should call SendInput."""
        mock_send.return_value = 1
        keyboard._held_keys.clear()

        result = keyboard.press_key("a")

        assert result is True
        assert mock_send.called
        assert "a" in keyboard._held_keys

    @patch.object(keyboard, "_send_input")
    def test_press_key_invalid(self, mock_send):
        """Unknown key should return False."""
        result = keyboard.press_key("nonexistent_key_xyz")

        assert result is False
        assert not mock_send.called

    @patch.object(keyboard, "_send_input")
    def test_release_key_valid(self, mock_send):
        """Valid key release should call SendInput."""
        mock_send.return_value = 1
        keyboard._held_keys.add("a")

        result = keyboard.release_key("a")

        assert result is True
        assert "a" not in keyboard._held_keys

    @patch.object(keyboard, "_send_input")
    def test_press_media_key(self, mock_send):
        """Media keys should use VK codes."""
        mock_send.return_value = 1
        keyboard._held_keys.clear()

        result = keyboard.press_key("media_play_pause")

        assert result is True
        # Check that VK code was used (not scan code)
        args = mock_send.call_args[0][0]
        assert len(args) == 1
        assert args[0].union.ki.wVk == keyboard.VK_MEDIA_PLAY_PAUSE


class TestTapKey:
    """Test tap_key function."""

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    def test_tap_key_calls_press_and_release(self, mock_press, mock_release):
        """Tap should call press then release."""
        mock_press.return_value = True
        mock_release.return_value = True

        result = keyboard.tap_key("a", hold_ms=1)

        assert result is True
        mock_press.assert_called_once_with("a")
        mock_release.assert_called_once_with("a")

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    def test_tap_key_fails_if_press_fails(self, mock_press, mock_release):
        """Tap should return False if press fails."""
        mock_press.return_value = False

        result = keyboard.tap_key("a")

        assert result is False
        assert not mock_release.called


class TestExecuteHotkey:
    """Test execute_hotkey function."""

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    def test_execute_hotkey_presses_all_keys(self, mock_press, mock_release):
        """Hotkey should press all keys in order."""
        mock_press.return_value = True
        mock_release.return_value = True

        keyboard.execute_hotkey(["ctrl", "shift", "s"], hold_ms=1, between_ms=1)

        assert mock_press.call_count == 3
        calls = [c[0][0] for c in mock_press.call_args_list]
        assert calls == ["ctrl", "shift", "s"]

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    def test_execute_hotkey_releases_in_reverse(self, mock_press, mock_release):
        """Hotkey should release keys in reverse order."""
        mock_press.return_value = True
        mock_release.return_value = True

        keyboard.execute_hotkey(["ctrl", "shift", "s"], hold_ms=1, between_ms=1)

        assert mock_release.call_count == 3
        calls = [c[0][0] for c in mock_release.call_args_list]
        assert calls == ["s", "shift", "ctrl"]

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    def test_execute_hotkey_empty_list(self, mock_press, mock_release):
        """Empty hotkey should return True without doing anything."""
        result = keyboard.execute_hotkey([])

        assert result is True
        assert not mock_press.called
        assert not mock_release.called

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    def test_execute_hotkey_releases_on_failure(self, mock_press, mock_release):
        """If a key fails to press, already pressed keys should be released."""
        # ctrl succeeds, shift fails
        mock_press.side_effect = [True, False]
        mock_release.return_value = True

        result = keyboard.execute_hotkey(
            ["ctrl", "shift", "s"], hold_ms=1, between_ms=1
        )

        assert result is False
        # Only ctrl was pressed, so only ctrl should be released
        mock_release.assert_called_once_with("ctrl")


class TestReleaseAllModifiers:
    """Test release_all_modifiers function."""

    @patch.object(keyboard, "_send_input")
    def test_releases_all_modifiers(self, mock_send):
        """Should send release for all modifier keys."""
        mock_send.return_value = 1
        keyboard._held_keys = {"ctrl", "alt", "shift"}

        keyboard.release_all_modifiers()

        # Should have called send_input multiple times for each modifier
        assert mock_send.call_count > 0
        # Held keys should not have modifiers
        assert "ctrl" not in keyboard._held_keys
        assert "alt" not in keyboard._held_keys
        assert "shift" not in keyboard._held_keys


class TestStateTracking:
    """Test key state tracking."""

    def test_get_held_keys_returns_copy(self):
        """get_held_keys should return a copy, not the original set."""
        keyboard._held_keys = {"a", "b"}

        held = keyboard.get_held_keys()
        held.add("c")

        assert "c" not in keyboard._held_keys

    def test_is_key_held(self):
        """is_key_held should check current state."""
        keyboard._held_keys = {"ctrl", "a"}

        assert keyboard.is_key_held("ctrl") is True
        assert keyboard.is_key_held("CTRL") is True  # Case insensitive
        assert keyboard.is_key_held("b") is False


class TestTypeText:
    """Test type_text function."""

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    @patch.object(keyboard, "tap_key")
    def test_type_lowercase(self, mock_tap, mock_press, mock_release):
        """Lowercase text should just tap keys."""
        mock_tap.return_value = True

        result = keyboard.type_text("abc", delay_ms=1)

        assert result is True
        assert mock_tap.call_count == 3
        # No shift needed
        assert not mock_press.called

    @patch.object(keyboard, "release_key")
    @patch.object(keyboard, "press_key")
    @patch.object(keyboard, "tap_key")
    def test_type_uppercase_uses_shift(self, mock_tap, mock_press, mock_release):
        """Uppercase should press shift."""
        mock_tap.return_value = True
        mock_press.return_value = True
        mock_release.return_value = True

        result = keyboard.type_text("A", delay_ms=1)

        assert result is True
        mock_press.assert_called_with("shift")
        mock_release.assert_called_with("shift")
