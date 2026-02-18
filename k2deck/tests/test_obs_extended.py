"""Extended tests for OBS client - error paths and edge cases."""

import time
from unittest.mock import MagicMock, patch

from k2deck.core.obs_client import OBSClientManager


class TestOBSClientErrorPaths:
    """Test OBSClientManager error and edge-case paths."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_connect_rate_limiting(self, mock_obs):
        """Should skip connect if called too quickly."""
        mock_obs.ReqClient.side_effect = Exception("fail")

        client = OBSClientManager()
        client._reconnect_interval = 10.0
        client._last_connect_attempt = time.time()  # just now

        # Should return current connected state without attempting
        result = client.connect()
        assert result is False  # not connected, but rate limited

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_connect_obs_sdk_error(self, mock_obs):
        """Should handle OBSSDKError during connect."""
        mock_obs.ReqClient.side_effect = Exception("auth failed")

        client = OBSClientManager()
        result = client.connect()

        assert result is False
        assert client.last_error is not None

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_disconnect_with_client(self, mock_obs):
        """Should disconnect and clear state."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        assert client.is_connected is True

        client.disconnect()
        assert client.is_connected is False
        mock_client.disconnect.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_disconnect_handles_error(self, mock_obs):
        """Should handle error during disconnect gracefully."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.disconnect.side_effect = Exception("already disconnected")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        client.disconnect()  # should not raise

        assert client.is_connected is False

    def test_disconnect_without_client(self):
        """Should handle disconnect when no client connected."""
        client = OBSClientManager()
        client.disconnect()  # should not raise
        assert client.is_connected is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_ensure_connected_already_connected(self, mock_obs):
        """Should return True if already connected."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()

        # Reset call count
        mock_obs.ReqClient.reset_mock()

        result = client._ensure_connected()
        assert result is True
        # Should not call ReqClient again
        mock_obs.ReqClient.assert_not_called()

    def test_get_client_returns_none_when_not_connected(self):
        """Should return None when connection fails."""
        client = OBSClientManager()
        with patch.object(client, "connect", return_value=False):
            result = client.get_client()
        assert result is None

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_set_scene_not_connected(self, mock_obs):
        """Should return False when not connected."""
        mock_obs.ReqClient.side_effect = Exception("fail")

        client = OBSClientManager()
        result = client.set_scene("Gaming")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_set_scene_request_error(self, mock_obs):
        """Should handle request error in set_scene."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.set_current_program_scene.side_effect = Exception("scene not found")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.set_scene("Nonexistent")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_source_not_found(self, mock_obs):
        """Should return False when source not found."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_items = MagicMock()
        mock_items.scene_items = [{"sourceName": "Other", "sceneItemId": 1}]
        mock_client.get_scene_item_list.return_value = mock_items
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_source_visibility("Main", "Missing")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_source_error(self, mock_obs):
        """Should handle error in toggle_source_visibility."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.get_scene_item_list.side_effect = Exception("scene error")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_source_visibility("Main", "Webcam")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_stream_invalid_action(self, mock_obs):
        """Should return False for invalid stream action."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_stream("invalid_action")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_stream_error(self, mock_obs):
        """Should handle error in toggle_stream."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.toggle_stream.side_effect = Exception("stream error")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_stream("toggle")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_record_start_stop(self, mock_obs):
        """Should handle record start and stop."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()

        assert client.toggle_record("start") is True
        mock_client.start_record.assert_called_once()

        assert client.toggle_record("stop") is True
        mock_client.stop_record.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_record_invalid_action(self, mock_obs):
        """Should return False for invalid record action."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_record("invalid")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_record_error(self, mock_obs):
        """Should handle error in toggle_record."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.toggle_record.side_effect = Exception("record error")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_record("toggle")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_mute_error(self, mock_obs):
        """Should handle error in toggle_mute."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.toggle_input_mute.side_effect = Exception("mute error")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_mute("Mic/Aux")
        assert result is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_get_scenes_not_connected(self, mock_obs):
        """Should return empty list when not connected."""
        mock_obs.ReqClient.side_effect = Exception("fail")

        client = OBSClientManager()
        result = client.get_scenes()
        assert result == []

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_get_scenes_error(self, mock_obs):
        """Should return empty list on error."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_client.get_scene_list.side_effect = Exception("scenes error")
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.get_scenes()
        assert result == []

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_set_source_visibility_explicit(self, mock_obs):
        """Should set explicit visibility (not toggle)."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_items = MagicMock()
        mock_items.scene_items = [{"sourceName": "Cam", "sceneItemId": 5}]
        mock_client.get_scene_item_list.return_value = mock_items
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_source_visibility("Main", "Cam", visible=True)

        assert result is True
        mock_client.set_scene_item_enabled.assert_called_once_with("Main", 5, True)
        # Should NOT call get_scene_item_enabled since visible is explicit
        mock_client.get_scene_item_enabled.assert_not_called()
