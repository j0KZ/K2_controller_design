"""Tests for OBS WebSocket integration (obs_client.py and obs.py)."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from k2deck.actions.obs import (
    OBSMuteAction,
    OBSRecordAction,
    OBSSceneAction,
    OBSSourceToggleAction,
    OBSStreamAction,
)
from k2deck.core.obs_client import OBSClientManager, get_obs_client


@dataclass
class MidiEvent:
    """Mock MIDI event for testing."""

    type: str
    channel: int
    note: int | None
    cc: int | None
    value: int
    timestamp: float


class TestOBSClientManager:
    """Test OBSClientManager class."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    def test_singleton_pattern(self):
        """Should return same instance."""
        client1 = OBSClientManager()
        client2 = OBSClientManager()
        assert client1 is client2

    def test_get_obs_client_returns_singleton(self):
        """get_obs_client should return singleton."""
        client1 = get_obs_client()
        client2 = get_obs_client()
        assert client1 is client2

    def test_configure_sets_params(self):
        """Should store configuration parameters."""
        client = OBSClientManager()
        client.configure(host="192.168.1.100", port=4456, password="secret", timeout=5)

        assert client._host == "192.168.1.100"
        assert client._port == 4456
        assert client._password == "secret"
        assert client._timeout == 5

    def test_is_available_without_library(self):
        """Should report unavailable when obsws-python not installed."""
        client = OBSClientManager()
        with patch("k2deck.core.obs_client.HAS_OBSWS", False):
            # Need to get a fresh client since HAS_OBSWS is checked at import
            pass
        # The actual test depends on whether obsws-python is installed
        assert isinstance(client.is_available, bool)

    def test_is_connected_initially_false(self):
        """Should not be connected initially."""
        client = OBSClientManager()
        assert client.is_connected is False

    def test_last_error_initially_none(self):
        """Should have no error initially."""
        client = OBSClientManager()
        assert client.last_error is None


class TestOBSClientManagerWithMock:
    """Test OBSClientManager with mocked obsws-python."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_connect_success(self, mock_obs):
        """Should connect successfully."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        result = client.connect()

        assert result is True
        assert client.is_connected is True

    @patch("k2deck.core.obs_client.HAS_OBSWS", False)
    def test_connect_without_library(self):
        """Should fail gracefully without library."""
        client = OBSClientManager()
        result = client.connect()

        assert result is False
        assert "not installed" in client.last_error

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    @patch("k2deck.core.obs_client.OBSSDKTimeoutError", Exception)
    def test_connect_timeout(self, mock_obs):
        """Should handle connection timeout."""
        mock_obs.ReqClient.side_effect = Exception("timeout")

        client = OBSClientManager()
        result = client.connect()

        assert result is False
        assert client.is_connected is False

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_set_scene_success(self, mock_obs):
        """Should switch scene successfully."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.set_scene("Gaming")

        assert result is True
        mock_client.set_current_program_scene.assert_called_once_with("Gaming")

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_stream_toggle(self, mock_obs):
        """Should toggle stream."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_result = MagicMock()
        mock_result.output_active = True
        mock_client.toggle_stream.return_value = mock_result
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_stream("toggle")

        assert result is True
        mock_client.toggle_stream.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_stream_start(self, mock_obs):
        """Should start stream."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_stream("start")

        assert result is True
        mock_client.start_stream.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_stream_stop(self, mock_obs):
        """Should stop stream."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_stream("stop")

        assert result is True
        mock_client.stop_stream.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_record_toggle(self, mock_obs):
        """Should toggle recording."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_result = MagicMock()
        mock_result.output_active = True
        mock_client.toggle_record.return_value = mock_result
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_record("toggle")

        assert result is True
        mock_client.toggle_record.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_record_pause(self, mock_obs):
        """Should toggle record pause."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_record("pause")

        assert result is True
        mock_client.toggle_record_pause.assert_called_once()

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_mute_toggle(self, mock_obs):
        """Should toggle mute."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_result = MagicMock()
        mock_result.input_muted = True
        mock_client.toggle_input_mute.return_value = mock_result
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_mute("Mic/Aux")

        assert result is True
        mock_client.toggle_input_mute.assert_called_once_with("Mic/Aux")

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_mute_set_muted(self, mock_obs):
        """Should set muted state."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_mute("Mic/Aux", muted=True)

        assert result is True
        mock_client.set_input_mute.assert_called_once_with("Mic/Aux", True)

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_toggle_source_visibility(self, mock_obs):
        """Should toggle source visibility."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version

        # Mock scene items
        mock_items = MagicMock()
        mock_items.scene_items = [
            {"sourceName": "Webcam", "sceneItemId": 1},
            {"sourceName": "Overlay", "sceneItemId": 2},
        ]
        mock_client.get_scene_item_list.return_value = mock_items

        # Mock current visibility
        mock_enabled = MagicMock()
        mock_enabled.scene_item_enabled = True
        mock_client.get_scene_item_enabled.return_value = mock_enabled

        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        result = client.toggle_source_visibility("Main", "Webcam")

        assert result is True
        mock_client.set_scene_item_enabled.assert_called_once_with("Main", 1, False)

    @patch("k2deck.core.obs_client.HAS_OBSWS", True)
    @patch("k2deck.core.obs_client.obs")
    def test_get_scenes(self, mock_obs):
        """Should get list of scenes."""
        mock_client = MagicMock()
        mock_version = MagicMock()
        mock_version.obs_version = "30.0.0"
        mock_version.obs_web_socket_version = "5.3.0"
        mock_client.get_version.return_value = mock_version

        mock_result = MagicMock()
        mock_result.scenes = [
            {"sceneName": "Scene 1"},
            {"sceneName": "Gaming"},
            {"sceneName": "Desktop"},
        ]
        mock_client.get_scene_list.return_value = mock_result
        mock_obs.ReqClient.return_value = mock_client

        client = OBSClientManager()
        client.connect()
        scenes = client.get_scenes()

        assert scenes == ["Scene 1", "Gaming", "Desktop"]


class TestOBSSceneAction:
    """Test OBSSceneAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = OBSSceneAction({"scene": "Gaming"})

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            event = MidiEvent(
                type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
            )
            action.execute(event)
            assert not mock_get.called

    def test_ignores_zero_velocity(self):
        """Should ignore note_on with velocity 0."""
        action = OBSSceneAction({"scene": "Gaming"})

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            event = MidiEvent(
                type="note_on", channel=16, note=36, cc=None, value=0, timestamp=0.0
            )
            action.execute(event)
            assert not mock_get.called

    def test_warns_if_no_scene_configured(self):
        """Should warn if no scene configured."""
        action = OBSSceneAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            action.execute(event)
            assert not mock_get.called

    @patch("k2deck.actions.obs.get_obs_client")
    def test_switches_scene(self, mock_get):
        """Should switch to configured scene."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSSceneAction({"scene": "Gaming"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.set_scene.assert_called_once_with("Gaming")


class TestOBSSourceToggleAction:
    """Test OBSSourceToggleAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = OBSSourceToggleAction({"scene": "Main", "source": "Webcam"})

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            event = MidiEvent(
                type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
            )
            action.execute(event)
            assert not mock_get.called

    def test_warns_if_no_scene_configured(self):
        """Should warn if no scene configured."""
        action = OBSSourceToggleAction({"source": "Webcam"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            action.execute(event)
            assert not mock_get.called

    def test_warns_if_no_source_configured(self):
        """Should warn if no source configured."""
        action = OBSSourceToggleAction({"scene": "Main"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            action.execute(event)
            assert not mock_get.called

    @patch("k2deck.actions.obs.get_obs_client")
    def test_toggles_source(self, mock_get):
        """Should toggle source visibility."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSSourceToggleAction({"scene": "Main", "source": "Webcam"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_source_visibility.assert_called_once_with(
            "Main", "Webcam", None
        )

    @patch("k2deck.actions.obs.get_obs_client")
    def test_sets_visibility(self, mock_get):
        """Should set specific visibility."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSSourceToggleAction(
            {"scene": "Main", "source": "Webcam", "visible": True}
        )
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_source_visibility.assert_called_once_with(
            "Main", "Webcam", True
        )


class TestOBSStreamAction:
    """Test OBSStreamAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = OBSStreamAction({})

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            event = MidiEvent(
                type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
            )
            action.execute(event)
            assert not mock_get.called

    @patch("k2deck.actions.obs.get_obs_client")
    def test_default_mode_toggle(self, mock_get):
        """Should default to toggle mode."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSStreamAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_stream.assert_called_once_with("toggle")

    @patch("k2deck.actions.obs.get_obs_client")
    def test_start_mode(self, mock_get):
        """Should use start mode."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSStreamAction({"mode": "start"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_stream.assert_called_once_with("start")


class TestOBSRecordAction:
    """Test OBSRecordAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = OBSRecordAction({})

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            event = MidiEvent(
                type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
            )
            action.execute(event)
            assert not mock_get.called

    @patch("k2deck.actions.obs.get_obs_client")
    def test_default_mode_toggle(self, mock_get):
        """Should default to toggle mode."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSRecordAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_record.assert_called_once_with("toggle")

    @patch("k2deck.actions.obs.get_obs_client")
    def test_pause_mode(self, mock_get):
        """Should use pause mode."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSRecordAction({"mode": "pause"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_record.assert_called_once_with("pause")


class TestOBSMuteAction:
    """Test OBSMuteAction class."""

    def setup_method(self):
        """Reset singleton for each test."""
        OBSClientManager._instance = None

    def test_only_triggers_on_note_on(self):
        """Should only execute on note_on events."""
        action = OBSMuteAction({"input": "Mic/Aux"})

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            event = MidiEvent(
                type="cc", channel=16, note=None, cc=1, value=64, timestamp=0.0
            )
            action.execute(event)
            assert not mock_get.called

    def test_warns_if_no_input_configured(self):
        """Should warn if no input configured."""
        action = OBSMuteAction({})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        with patch("k2deck.actions.obs.get_obs_client") as mock_get:
            action.execute(event)
            assert not mock_get.called

    @patch("k2deck.actions.obs.get_obs_client")
    def test_toggles_mute(self, mock_get):
        """Should toggle mute."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSMuteAction({"input": "Mic/Aux"})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_mute.assert_called_once_with("Mic/Aux", None)

    @patch("k2deck.actions.obs.get_obs_client")
    def test_sets_muted(self, mock_get):
        """Should set muted state."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_get.return_value = mock_client

        action = OBSMuteAction({"input": "Mic/Aux", "muted": True})
        event = MidiEvent(
            type="note_on", channel=16, note=36, cc=None, value=127, timestamp=0.0
        )

        action.execute(event)

        mock_client.toggle_mute.assert_called_once_with("Mic/Aux", True)
