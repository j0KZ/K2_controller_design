"""Tests for Web UI Backend API endpoints."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip tests if fastapi not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from k2deck.core.analog_state import AnalogStateManager


class TestConfigAPI:
    """Test /api/config endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test client with temp config directory."""
        # Reset singleton
        AnalogStateManager._instance = None

        # Create temp config
        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()

        # Create default profile
        default_config = {
            "name": "default",
            "mappings": {
                "note_on": {"36": {"action": "hotkey", "keys": ["f1"]}},
                "cc": {"16": {"action": "volume", "target": "Spotify.exe"}},
            },
        }
        (self.config_dir / "default.json").write_text(json.dumps(default_config))

        # Patch config directory
        with patch("k2deck.web.routes.config.CONFIG_DIR", self.config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", self.config_dir):
                from k2deck.web.server import create_app

                app = create_app()
                self.client = TestClient(app)
                yield

    def test_get_config(self):
        """Should return active profile config."""
        response = self.client.get("/api/config")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "default"
        assert "mappings" in data

    def test_put_config_valid(self):
        """Should update config with valid data."""
        new_config = {
            "name": "updated",
            "mappings": {
                "note_on": {"36": {"action": "hotkey", "keys": ["f2"]}},
                "cc": {},
            },
        }

        response = self.client.put("/api/config", json={"config": new_config})
        assert response.status_code == 200

        # Verify saved
        response = self.client.get("/api/config")
        assert response.json()["name"] == "updated"

    def test_put_config_invalid(self):
        """Should reject invalid config."""
        invalid_config = {
            "mappings": {"note_on": "not_an_object"},  # Invalid
        }

        response = self.client.put("/api/config", json={"config": invalid_config})
        assert response.status_code == 400

    def test_validate_config_valid(self):
        """Should validate valid config."""
        config = {
            "mappings": {
                "note_on": {"36": {"action": "hotkey"}},
                "cc": {},
            },
        }

        response = self.client.post("/api/config/validate", json={"config": config})
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_validate_config_invalid(self):
        """Should report errors for invalid config."""
        config = {"mappings": "invalid"}

        response = self.client.post("/api/config/validate", json={"config": config})
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestProfilesAPI:
    """Test /api/profiles endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test client with temp config directory."""
        AnalogStateManager._instance = None

        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()

        # Create default profile
        default_config = {"name": "default", "mappings": {"note_on": {}, "cc": {}}}
        (self.config_dir / "default.json").write_text(json.dumps(default_config))

        # Create another profile
        streaming_config = {"name": "streaming", "mappings": {"note_on": {}, "cc": {}}}
        (self.config_dir / "streaming.json").write_text(json.dumps(streaming_config))

        with patch("k2deck.web.routes.config.CONFIG_DIR", self.config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", self.config_dir):
                from k2deck.web.routes.profiles import set_active_profile
                set_active_profile("default")  # Reset active profile

                from k2deck.web.server import create_app
                app = create_app()
                self.client = TestClient(app)
                yield

    def test_list_profiles(self):
        """Should list all profiles."""
        response = self.client.get("/api/profiles")
        assert response.status_code == 200

        data = response.json()
        names = [p["name"] for p in data["profiles"]]
        assert "default" in names
        assert "streaming" in names
        assert data["active"] == "default"

    def test_create_profile(self):
        """Should create new profile."""
        response = self.client.post("/api/profiles", json={"name": "gaming"})
        assert response.status_code == 200

        # Verify created
        response = self.client.get("/api/profiles")
        names = [p["name"] for p in response.json()["profiles"]]
        assert "gaming" in names

    def test_create_profile_copy_from(self):
        """Should copy from existing profile."""
        response = self.client.post(
            "/api/profiles",
            json={"name": "streaming_copy", "copy_from": "streaming"},
        )
        assert response.status_code == 200

        # Verify content copied
        response = self.client.get("/api/profiles/streaming_copy")
        assert response.json()["name"] == "streaming"

    def test_create_profile_duplicate(self):
        """Should reject duplicate profile name."""
        response = self.client.post("/api/profiles", json={"name": "default"})
        assert response.status_code == 409

    def test_create_profile_invalid_name(self):
        """Should reject invalid profile names."""
        response = self.client.post("/api/profiles", json={"name": "has spaces"})
        assert response.status_code == 400

        response = self.client.post("/api/profiles", json={"name": ""})
        assert response.status_code == 400

    def test_get_profile(self):
        """Should get specific profile."""
        response = self.client.get("/api/profiles/default")
        assert response.status_code == 200
        assert response.json()["name"] == "default"

    def test_get_profile_not_found(self):
        """Should return 404 for unknown profile."""
        response = self.client.get("/api/profiles/nonexistent")
        assert response.status_code == 404

    def test_update_profile(self):
        """Should update profile config."""
        new_config = {"name": "streaming_updated", "mappings": {"note_on": {}, "cc": {}}}

        response = self.client.put(
            "/api/profiles/streaming", json={"config": new_config}
        )
        assert response.status_code == 200

        # Verify updated
        response = self.client.get("/api/profiles/streaming")
        assert response.json()["name"] == "streaming_updated"

    def test_delete_profile(self):
        """Should delete profile."""
        response = self.client.delete("/api/profiles/streaming")
        assert response.status_code == 200

        # Verify deleted
        response = self.client.get("/api/profiles/streaming")
        assert response.status_code == 404

    def test_delete_default_profile(self):
        """Should not allow deleting default profile."""
        response = self.client.delete("/api/profiles/default")
        assert response.status_code == 400

    def test_delete_active_profile(self):
        """Should not allow deleting active profile."""
        # Activate streaming profile
        self.client.put("/api/profiles/streaming/activate")

        # Try to delete it
        response = self.client.delete("/api/profiles/streaming")
        assert response.status_code == 400

    def test_activate_profile(self):
        """Should activate a profile."""
        response = self.client.put("/api/profiles/streaming/activate")
        assert response.status_code == 200
        assert response.json()["previous"] == "default"

        # Verify active
        response = self.client.get("/api/profiles")
        assert response.json()["active"] == "streaming"


class TestK2API:
    """Test /api/k2 endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test client."""
        AnalogStateManager._instance = None

        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()
        (self.config_dir / "default.json").write_text(
            json.dumps({"name": "default", "mappings": {"note_on": {}, "cc": {}}})
        )

        with patch("k2deck.web.routes.config.CONFIG_DIR", self.config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", self.config_dir):
                from k2deck.web.server import create_app
                app = create_app()
                self.client = TestClient(app)
                yield

    def test_get_layout(self):
        """Should return K2 hardware layout."""
        response = self.client.get("/api/k2/layout")
        assert response.status_code == 200

        layout = response.json()
        assert layout["totalControls"] == 52
        assert layout["totalLeds"] == 34
        assert layout["layers"] == 3
        assert layout["midiChannel"] == 16
        assert len(layout["rows"]) > 0

    def test_get_state(self):
        """Should return K2 state."""
        response = self.client.get("/api/k2/state")
        assert response.status_code == 200

        state = response.json()
        assert "connected" in state
        assert "layer" in state
        assert "folder" in state
        assert "leds" in state
        assert "analog" in state

    def test_get_layer(self):
        """Should return current layer."""
        response = self.client.get("/api/k2/state/layer")
        assert response.status_code == 200
        assert "layer" in response.json()

    def test_set_layer_valid(self):
        """Should set layer to valid value."""
        response = self.client.put("/api/k2/state/layer", json={"layer": 2})
        assert response.status_code == 200
        assert response.json()["layer"] == 2

    def test_set_layer_invalid(self):
        """Should reject invalid layer."""
        response = self.client.put("/api/k2/state/layer", json={"layer": 5})
        assert response.status_code == 400

    def test_get_analog(self):
        """Should return analog positions."""
        response = self.client.get("/api/k2/state/analog")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_get_midi_devices(self):
        """Should return MIDI device list."""
        with patch("mido.get_input_names", return_value=["XONE:K2"]):
            with patch("mido.get_output_names", return_value=["XONE:K2"]):
                response = self.client.get("/api/k2/midi/devices")
                assert response.status_code == 200
                assert isinstance(response.json(), list)

    def test_get_midi_status(self):
        """Should return MIDI status."""
        response = self.client.get("/api/k2/midi/status")
        assert response.status_code == 200

        status = response.json()
        assert "connected" in status
        assert "port" in status


class TestIntegrationsAPI:
    """Test /api/integrations endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test client."""
        AnalogStateManager._instance = None

        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()
        (self.config_dir / "default.json").write_text(
            json.dumps({"name": "default", "mappings": {"note_on": {}, "cc": {}}})
        )

        with patch("k2deck.web.routes.config.CONFIG_DIR", self.config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", self.config_dir):
                from k2deck.web.server import create_app
                app = create_app()
                self.client = TestClient(app)
                yield

    def test_get_all_integrations(self):
        """Should return status of all integrations."""
        response = self.client.get("/api/integrations")
        assert response.status_code == 200

        data = response.json()
        assert "obs" in data
        assert "spotify" in data
        assert "twitch" in data

    def test_get_obs_status(self):
        """Should return OBS status."""
        response = self.client.get("/api/integrations/obs/status")
        assert response.status_code == 200

        status = response.json()
        assert status["name"] == "obs"
        assert "available" in status
        assert "connected" in status

    def test_get_spotify_status(self):
        """Should return Spotify status."""
        response = self.client.get("/api/integrations/spotify/status")
        assert response.status_code == 200
        assert response.json()["name"] == "spotify"

    def test_get_twitch_status(self):
        """Should return Twitch status."""
        response = self.client.get("/api/integrations/twitch/status")
        assert response.status_code == 200
        assert response.json()["name"] == "twitch"

    def test_get_unknown_integration(self):
        """Should return 422 for unknown integration."""
        response = self.client.get("/api/integrations/unknown/status")
        assert response.status_code == 422  # Validation error


class TestWebSocket:
    """Test WebSocket functionality."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test client."""
        AnalogStateManager._instance = None

        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()
        (self.config_dir / "default.json").write_text(
            json.dumps({"name": "default", "mappings": {"note_on": {}, "cc": {}}})
        )

        with patch("k2deck.web.routes.config.CONFIG_DIR", self.config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", self.config_dir):
                from k2deck.web.server import create_app
                app = create_app()
                self.client = TestClient(app)
                yield

    def test_websocket_connect(self):
        """Should accept WebSocket connection."""
        with self.client.websocket_connect("/ws/events") as websocket:
            # Should receive initial analog state
            data = websocket.receive_json()
            assert data["type"] == "analog_state"

    def test_websocket_receives_analog_state(self):
        """Should receive initial analog state on connect."""
        # Pre-populate some analog state
        from k2deck.core.analog_state import get_analog_state_manager
        manager = get_analog_state_manager()
        manager.update(16, 64)

        with self.client.websocket_connect("/ws/events") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "analog_state"
            assert "controls" in data["data"]
