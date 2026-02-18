"""Extended tests for Web UI Backend API endpoints.

Covers: config export/import, LED endpoints, folder endpoint,
MIDI reconnect, integration connect/disconnect, WebSocket messages.
"""

import io
import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from k2deck.core.analog_state import AnalogStateManager


class TestConfigExportImport:
    """Test /api/config export and import endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test client with temp config directory."""
        AnalogStateManager._instance = None

        self.config_dir = tmp_path / "config"
        self.config_dir.mkdir()

        default_config = {
            "name": "default",
            "mappings": {
                "note_on": {"36": {"action": "hotkey", "keys": ["f1"]}},
                "cc": {},
            },
        }
        (self.config_dir / "default.json").write_text(json.dumps(default_config))

        with patch("k2deck.web.routes.config.CONFIG_DIR", self.config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", self.config_dir):
                from k2deck.web.server import create_app

                app = create_app()
                self.client = TestClient(app)
                yield

    def test_export_config(self):
        """Should export config as JSON file."""
        response = self.client.get("/api/config/export")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        # Should be valid JSON
        data = json.loads(response.content)
        assert data["name"] == "default"
        assert "mappings" in data

    def test_import_valid_config(self):
        """Should import valid JSON config."""
        config = {
            "name": "imported",
            "mappings": {
                "note_on": {"36": {"action": "hotkey", "keys": ["f5"]}},
                "cc": {},
            },
        }
        content = json.dumps(config).encode("utf-8")

        response = self.client.post(
            "/api/config/import",
            files={"file": ("test.json", io.BytesIO(content), "application/json")},
        )
        assert response.status_code == 200

        # Verify imported
        response = self.client.get("/api/config")
        assert response.json()["name"] == "imported"

    def test_import_non_json_file(self):
        """Should reject non-JSON filename."""
        content = b'{"name": "test", "mappings": {"note_on": {}, "cc": {}}}'

        response = self.client.post(
            "/api/config/import",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert response.status_code == 400

    def test_import_invalid_json(self):
        """Should reject invalid JSON content."""
        content = b"not json {{{{"

        response = self.client.post(
            "/api/config/import",
            files={"file": ("test.json", io.BytesIO(content), "application/json")},
        )
        assert response.status_code == 400

    def test_import_invalid_config(self):
        """Should reject config that fails validation."""
        config = {"mappings": "invalid_string"}
        content = json.dumps(config).encode("utf-8")

        response = self.client.post(
            "/api/config/import",
            files={"file": ("test.json", io.BytesIO(content), "application/json")},
        )
        assert response.status_code == 400


class TestK2LedEndpoints:
    """Test /api/k2/state/leds endpoints."""

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

    def test_get_led_states(self):
        """Should return LED states dict."""
        response = self.client.get("/api/k2/state/leds")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_set_led_valid_note(self):
        """Should set LED for valid note."""
        with patch("k2deck.feedback.led_manager.get_led_manager") as mock_get:
            mock_mgr = MagicMock()
            mock_get.return_value = mock_mgr

            response = self.client.put(
                "/api/k2/state/leds/36",
                json={"note": 36, "color": "green", "on": True},
            )
            assert response.status_code == 200
            mock_mgr.set_led.assert_called_with(36, "green")

    def test_set_led_off(self):
        """Should turn off LED."""
        with patch("k2deck.feedback.led_manager.get_led_manager") as mock_get:
            mock_mgr = MagicMock()
            mock_get.return_value = mock_mgr

            response = self.client.put(
                "/api/k2/state/leds/36",
                json={"note": 36, "color": None, "on": False},
            )
            assert response.status_code == 200
            mock_mgr.set_led_off.assert_called_with(36)

    def test_set_led_invalid_note(self):
        """Should reject invalid LED note."""
        response = self.client.put(
            "/api/k2/state/leds/99",
            json={"note": 99, "color": "green", "on": True},
        )
        assert response.status_code == 400

    def test_set_led_invalid_color(self):
        """Should reject invalid LED color."""
        response = self.client.put(
            "/api/k2/state/leds/36",
            json={"note": 36, "color": "blue", "on": True},
        )
        assert response.status_code == 400


class TestK2FolderEndpoint:
    """Test /api/k2/state/folder endpoint."""

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

    def test_get_folder_state(self):
        """Should return current folder."""
        response = self.client.get("/api/k2/state/folder")
        assert response.status_code == 200
        assert "folder" in response.json()


class TestMidiReconnect:
    """Test /api/k2/midi/reconnect endpoint."""

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

    def test_reconnect_midi(self):
        """Should trigger MIDI reconnection."""
        response = self.client.post("/api/k2/midi/reconnect")
        assert response.status_code == 200
        assert "message" in response.json()


class TestIntegrationConnectDisconnect:
    """Test integration connect/disconnect endpoints."""

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

    def test_connect_spotify_returns_501(self):
        """Should return 501 for Spotify connect (OAuth not implemented)."""
        response = self.client.post("/api/integrations/spotify/connect")
        assert response.status_code == 501

    def test_connect_twitch_returns_501(self):
        """Should return 501 for Twitch connect (OAuth not implemented)."""
        response = self.client.post("/api/integrations/twitch/connect")
        assert response.status_code == 501

    def test_disconnect_spotify_returns_501(self):
        """Should return 501 for Spotify disconnect (not implemented)."""
        response = self.client.post("/api/integrations/spotify/disconnect")
        assert response.status_code == 501

    def test_disconnect_twitch_returns_501(self):
        """Should return 501 for Twitch disconnect (not implemented)."""
        response = self.client.post("/api/integrations/twitch/disconnect")
        assert response.status_code == 501


class TestWebSocketMessages:
    """Test WebSocket message handling."""

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

    def test_websocket_set_led(self):
        """Should handle set_led command."""
        with patch("k2deck.feedback.led_manager.get_led_manager") as mock_get:
            mock_mgr = MagicMock()
            mock_get.return_value = mock_mgr

            with self.client.websocket_connect("/ws/events") as websocket:
                # Receive initial analog state
                websocket.receive_json()

                # Send set_led command
                websocket.send_json(
                    {
                        "type": "set_led",
                        "data": {"note": 36, "color": "green"},
                    }
                )

                # Give time for message processing
                import time

                time.sleep(0.1)

            mock_mgr.set_led.assert_called_with(36, "green")

    def test_websocket_set_led_off(self):
        """Should handle set_led off command."""
        with patch("k2deck.feedback.led_manager.get_led_manager") as mock_get:
            mock_mgr = MagicMock()
            mock_get.return_value = mock_mgr

            with self.client.websocket_connect("/ws/events") as websocket:
                websocket.receive_json()

                websocket.send_json(
                    {
                        "type": "set_led",
                        "data": {"note": 36, "color": None},
                    }
                )

                import time

                time.sleep(0.1)

            mock_mgr.set_led_off.assert_called_with(36)
