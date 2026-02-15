"""Tests for k2deck.core.autostart — Windows auto-start management."""

import sys
from pathlib import Path
from unittest.mock import patch

from k2deck.core.autostart import (
    STARTUP_FILENAME,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
)


class TestIsAutostartEnabled:
    """Tests for is_autostart_enabled()."""

    def test_returns_false_when_no_file(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            assert is_autostart_enabled() is False

    def test_returns_true_when_file_exists(self, tmp_path):
        (tmp_path / STARTUP_FILENAME).write_text("dummy")
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            assert is_autostart_enabled() is True


class TestEnableAutostart:
    """Tests for enable_autostart()."""

    def test_creates_vbs_file(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            vbs_path = tmp_path / STARTUP_FILENAME
            assert vbs_path.exists()

    def test_vbs_contains_wscript_shell(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert 'CreateObject("WScript.Shell")' in content

    def test_vbs_contains_python_executable(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert sys.executable in content

    def test_vbs_hidden_window_style(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert ", 0, False" in content

    def test_vbs_contains_k2deck_module(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert "k2deck" in content
            assert "-m" in content

    def test_includes_config_arg(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            config = Path("C:/my/config.json")
            enable_autostart(config_path=config)
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert "--config" in content
            assert str(config) in content

    def test_includes_device_arg(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart(device_name="MY_K2")
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert "--device" in content
            assert "MY_K2" in content

    def test_includes_debug_flag(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart(debug=True)
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert "--debug" in content

    def test_default_args_minimal(self, tmp_path):
        """Default invocation omits optional args."""
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert "--config" not in content
            assert "--device" not in content
            assert "--debug" not in content

    def test_handles_spaced_python_path(self, tmp_path):
        """VBS handles Python paths with spaces correctly."""
        spaced_path = "C:\\Program Files\\Python312\\python.exe"
        with (
            patch("k2deck.core.autostart.STARTUP_DIR", tmp_path),
            patch("k2deck.core.autostart.sys") as mock_sys,
        ):
            mock_sys.executable = spaced_path
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            # Path should be in the VBS wrapped with chr(34)
            assert "Program Files" in content
            assert "chr(34)" in content

    def test_sets_current_directory(self, tmp_path):
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            enable_autostart()
            content = (tmp_path / STARTUP_FILENAME).read_text()
            assert "CurrentDirectory" in content


class TestDisableAutostart:
    """Tests for disable_autostart()."""

    def test_removes_existing_file(self, tmp_path):
        vbs_path = tmp_path / STARTUP_FILENAME
        vbs_path.write_text("dummy")
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            disable_autostart()
            assert not vbs_path.exists()

    def test_noop_when_no_file(self, tmp_path):
        """Does not raise when file doesn't exist."""
        with patch("k2deck.core.autostart.STARTUP_DIR", tmp_path):
            disable_autostart()  # Should not raise
