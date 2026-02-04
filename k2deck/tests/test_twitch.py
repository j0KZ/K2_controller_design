"""Tests for twitch.py and twitch_client.py - Twitch integration."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass

from k2deck.core.twitch_client import TwitchClient, HAS_TWITCH, get_twitch_client
from k2deck.actions.twitch import (
    TwitchMarkerAction,
    TwitchClipAction,
    TwitchChatAction,
    TwitchTitleAction,
    TwitchGameAction,
)


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""
    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestTwitchClient:
    """Test TwitchClient class."""

    def setup_method(self):
        """Reset singleton for each test."""
        TwitchClient._instance = None

    def test_singleton_pattern(self):
        """Should return same instance."""
        client1 = TwitchClient()
        client2 = TwitchClient()
        assert client1 is client2

    def test_get_twitch_client_returns_singleton(self):
        """get_twitch_client should return singleton."""
        client1 = get_twitch_client()
        client2 = get_twitch_client()
        assert client1 is client2

    def test_is_available_reflects_import(self):
        """is_available should reflect whether twitchAPI is installed."""
        client = TwitchClient()
        # This test just verifies the property works
        assert isinstance(client.is_available, bool)

    def test_not_connected_initially(self):
        """Should not be connected initially."""
        client = TwitchClient()
        assert client.is_connected is False

    def test_configure_sets_credentials(self):
        """Should configure credentials."""
        client = TwitchClient()
        client.configure("test_id", "test_secret")
        assert client._client_id == "test_id"
        assert client._client_secret == "test_secret"

    def test_configure_uses_env_vars(self):
        """Should use environment variables if no args provided."""
        with patch.dict("os.environ", {
            "TWITCH_CLIENT_ID": "env_id",
            "TWITCH_CLIENT_SECRET": "env_secret"
        }):
            client = TwitchClient()
            client.configure()
            assert client._client_id == "env_id"
            assert client._client_secret == "env_secret"

    @pytest.mark.skipif(not HAS_TWITCH, reason="twitchAPI not installed")
    def test_initialize_fails_without_credentials(self):
        """Should fail to initialize without credentials."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove any existing env vars
            import os
            os.environ.pop("TWITCH_CLIENT_ID", None)
            os.environ.pop("TWITCH_CLIENT_SECRET", None)

            client = TwitchClient()
            client._client_id = ""
            client._client_secret = ""
            result = client.initialize()
            assert result is False

    def test_rate_limit_enforced(self):
        """Should enforce rate limiting."""
        client = TwitchClient()
        # First call should pass
        assert client._rate_limit() is True
        # Immediate second call should be blocked
        assert client._rate_limit() is False

    def test_rate_limit_allows_after_interval(self):
        """Should allow action after interval."""
        import time
        client = TwitchClient()
        client._last_action_time = time.time() - 2.0  # 2 seconds ago
        assert client._rate_limit() is True


class TestTwitchMarkerAction:
    """Test TwitchMarkerAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        TwitchClient._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = TwitchMarkerAction({"description": "test"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)

        with patch("k2deck.core.twitch_client.get_twitch_client") as mock_get:
            action.execute(event)
            mock_get.assert_not_called()

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = TwitchMarkerAction({"description": "test"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0)

        with patch("k2deck.core.twitch_client.get_twitch_client") as mock_get:
            action.execute(event)
            mock_get.assert_not_called()

    def test_calls_create_marker(self):
        """Should call create_marker on connected client."""
        action = TwitchMarkerAction({"description": "highlight"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.create_marker.assert_called_once_with("highlight")

    def test_skips_if_not_available(self):
        """Should skip if twitchAPI not installed."""
        action = TwitchMarkerAction({"description": "test"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = False

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.create_marker.assert_not_called()

    def test_skips_if_not_connected(self):
        """Should skip if not connected to Twitch."""
        action = TwitchMarkerAction({"description": "test"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = False

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.create_marker.assert_not_called()


class TestTwitchClipAction:
    """Test TwitchClipAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        TwitchClient._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = TwitchClipAction({})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)

        with patch("k2deck.core.twitch_client.get_twitch_client") as mock_get:
            action.execute(event)
            mock_get.assert_not_called()

    def test_calls_create_clip(self):
        """Should call create_clip on connected client."""
        action = TwitchClipAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True
        mock_client.create_clip.return_value = "https://clips.twitch.tv/test123"

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.create_clip.assert_called_once()


class TestTwitchChatAction:
    """Test TwitchChatAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        TwitchClient._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = TwitchChatAction({"message": "hello"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)

        with patch("k2deck.core.twitch_client.get_twitch_client") as mock_get:
            action.execute(event)
            mock_get.assert_not_called()

    def test_calls_send_chat(self):
        """Should call send_chat with message."""
        action = TwitchChatAction({"message": "Thanks for watching!"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.send_chat.assert_called_once_with("Thanks for watching!")

    def test_warns_if_no_message(self):
        """Should warn if no message configured."""
        action = TwitchChatAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.send_chat.assert_not_called()


class TestTwitchTitleAction:
    """Test TwitchTitleAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        TwitchClient._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = TwitchTitleAction({"title": "New Title"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)

        with patch("k2deck.core.twitch_client.get_twitch_client") as mock_get:
            action.execute(event)
            mock_get.assert_not_called()

    def test_calls_update_title(self):
        """Should call update_title with title."""
        action = TwitchTitleAction({"title": "Just Chatting!"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.update_title.assert_called_once_with("Just Chatting!")

    def test_warns_if_no_title(self):
        """Should warn if no title configured."""
        action = TwitchTitleAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.update_title.assert_not_called()


class TestTwitchGameAction:
    """Test TwitchGameAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        TwitchClient._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = TwitchGameAction({"game": "Minecraft"})
        event = MidiEvent(type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0)

        with patch("k2deck.core.twitch_client.get_twitch_client") as mock_get:
            action.execute(event)
            mock_get.assert_not_called()

    def test_calls_update_game(self):
        """Should call update_game with game name."""
        action = TwitchGameAction({"game": "Just Chatting"})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.update_game.assert_called_once_with("Just Chatting")

    def test_warns_if_no_game(self):
        """Should warn if no game configured."""
        action = TwitchGameAction({})
        event = MidiEvent(type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0)

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch("k2deck.core.twitch_client.get_twitch_client", return_value=mock_client):
            action.execute(event)
            mock_client.update_game.assert_not_called()
