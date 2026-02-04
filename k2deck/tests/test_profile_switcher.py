"""Tests for profile_switcher.py - Profile auto-switch based on active app."""

import time
import pytest
from unittest.mock import patch, MagicMock

from k2deck.core.profile_switcher import ProfileAutoSwitcher
from k2deck.core.context import AppInfo


class TestProfileAutoSwitcherConfig:
    """Test ProfileAutoSwitcher configuration."""

    def test_disabled_by_default(self):
        """Should be disabled by default."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        assert switcher.enabled is False

    def test_disabled_with_empty_config(self):
        """Should be disabled with empty config."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.configure({})
        assert switcher.enabled is False

    def test_disabled_without_rules(self):
        """Should be disabled if enabled but no rules."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.configure({"enabled": True, "rules": []})
        assert switcher.enabled is False

    def test_enabled_with_rules(self):
        """Should be enabled with valid config."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs.exe", "profile": "streaming"}],
            "default_profile": "default"
        })
        assert switcher.enabled is True

    def test_custom_check_interval(self):
        """Should accept custom check interval."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "test.exe", "profile": "test"}],
            "check_interval": 1.5
        })
        assert switcher._check_interval == 1.5


class TestProfileAutoSwitcherMatching:
    """Test rule matching logic."""

    def test_matches_exact_app_name(self):
        """Should match exact app name."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs64.exe", "profile": "streaming"}],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs64.exe", title="OBS", pid=1234, hwnd=5678)
            switcher._check_and_switch()

        assert switched_to == ["streaming"]

    def test_matches_partial_app_name(self):
        """Should match partial app name (case-insensitive)."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs", "profile": "streaming"}],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs64.exe", title="OBS", pid=1234, hwnd=5678)
            switcher._check_and_switch()

        assert switched_to == ["streaming"]

    def test_case_insensitive_matching(self):
        """Matching should be case insensitive."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "OBS", "profile": "streaming"}],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs64.exe", title="OBS", pid=1234, hwnd=5678)
            switcher._check_and_switch()

        assert switched_to == ["streaming"]

    def test_first_matching_rule_wins(self):
        """Should use first matching rule."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [
                {"app": "obs", "profile": "streaming"},
                {"app": "obs64", "profile": "advanced_streaming"},
            ],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs64.exe", title="OBS", pid=1234, hwnd=5678)
            switcher._check_and_switch()

        # First rule "obs" matches first
        assert switched_to == ["streaming"]

    def test_falls_back_to_default(self):
        """Should use default profile if no rules match."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs.exe", "profile": "streaming"}],
            "default_profile": "general"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="notepad.exe", title="Untitled", pid=1234, hwnd=5678)
            switcher._check_and_switch()

        assert switched_to == ["general"]

    def test_no_switch_if_same_profile(self):
        """Should not trigger callback if profile unchanged."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs.exe", "profile": "streaming"}],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs.exe", title="OBS", pid=1234, hwnd=5678)

            # First call triggers switch
            switcher._check_and_switch()
            assert switched_to == ["streaming"]

            # Second call with same app should not trigger
            switcher._check_and_switch()
            assert switched_to == ["streaming"]  # Still just one

    def test_no_action_if_no_foreground_app(self):
        """Should do nothing if no foreground app detected."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs.exe", "profile": "streaming"}],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = None
            switcher._check_and_switch()

        assert switched_to == []


class TestProfileAutoSwitcherLifecycle:
    """Test start/stop lifecycle."""

    def test_start_does_nothing_if_disabled(self):
        """start() should do nothing if not enabled."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.start()
        assert switcher._running is False
        assert switcher._thread is None

    def test_start_creates_thread_if_enabled(self):
        """start() should create background thread if enabled."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "test.exe", "profile": "test"}],
            "check_interval": 0.1
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = None
            switcher.start()
            assert switcher._running is True
            assert switcher._thread is not None
            assert switcher._thread.is_alive()

            # Stop the thread
            switcher.stop()
            assert switcher._running is False

    def test_stop_joins_thread(self):
        """stop() should wait for thread to finish."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "test.exe", "profile": "test"}],
            "check_interval": 0.05
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = None
            switcher.start()
            switcher.stop()
            assert not switcher._thread or not switcher._thread.is_alive()


class TestProfileAutoSwitcherManual:
    """Test manual control methods."""

    def test_set_profile_updates_current(self):
        """set_profile() should update current profile."""
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: None)
        switcher.set_profile("custom")
        assert switcher.current_profile == "custom"

    def test_force_check_triggers_check(self):
        """force_check() should trigger immediate check."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        switcher.configure({
            "enabled": True,
            "rules": [{"app": "obs.exe", "profile": "streaming"}],
            "default_profile": "default"
        })

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs.exe", title="OBS", pid=1234, hwnd=5678)
            switcher.force_check()

        assert switched_to == ["streaming"]

    def test_force_check_does_nothing_if_disabled(self):
        """force_check() should do nothing if disabled."""
        switched_to = []
        switcher = ProfileAutoSwitcher(on_profile_switch=lambda x: switched_to.append(x))
        # Not configured/enabled

        with patch('k2deck.core.profile_switcher.get_foreground_app') as mock_fg:
            mock_fg.return_value = AppInfo(name="obs.exe", title="OBS", pid=1234, hwnd=5678)
            switcher.force_check()

        assert switched_to == []
