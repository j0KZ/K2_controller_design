"""Tests for integrations routes - status helpers, OBS connect/disconnect."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from k2deck.core.analog_state import AnalogStateManager


class TestIntegrationStatusHelpers:
    """Test integration status endpoints."""

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
        """Should return status for all 3 integrations."""
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
        data = response.json()
        assert data["name"] == "obs"
        assert "available" in data
        assert "connected" in data
        assert "status" in data

    def test_get_spotify_status(self):
        """Should return Spotify status."""
        response = self.client.get("/api/integrations/spotify/status")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "spotify"

    def test_get_twitch_status(self):
        """Should return Twitch status."""
        response = self.client.get("/api/integrations/twitch/status")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "twitch"

    def test_invalid_integration_name(self):
        """Should return 422 for invalid integration name."""
        response = self.client.get("/api/integrations/invalid/status")
        assert response.status_code == 422

    def test_obs_status_with_mocked_connected_client(self):
        """Should return connected status with mocked OBS client."""
        from k2deck.web.routes.integrations import IntegrationStatus

        mock_status = IntegrationStatus(
            name="obs",
            available=True,
            connected=True,
            status="connected",
            details={"scenes": ["Scene 1"]},
        )

        with patch(
            "k2deck.web.routes.integrations._get_obs_status", return_value=mock_status
        ):
            response = self.client.get("/api/integrations/obs/status")
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["status"] == "connected"

    def test_obs_status_with_mocked_disconnected_client(self):
        """Should return disconnected status."""
        from k2deck.web.routes.integrations import IntegrationStatus

        mock_status = IntegrationStatus(
            name="obs",
            available=True,
            connected=False,
            status="disconnected",
            error="Connection refused",
        )

        with patch(
            "k2deck.web.routes.integrations._get_obs_status", return_value=mock_status
        ):
            response = self.client.get("/api/integrations/obs/status")
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
            assert data["error"] == "Connection refused"

    def test_spotify_status_with_mocked_connected_client(self):
        """Should return connected Spotify status."""
        from k2deck.web.routes.integrations import IntegrationStatus

        mock_status = IntegrationStatus(
            name="spotify",
            available=True,
            connected=True,
            status="connected",
            details={"user": "testuser"},
        )

        with patch(
            "k2deck.web.routes.integrations._get_spotify_status",
            return_value=mock_status,
        ):
            response = self.client.get("/api/integrations/spotify/status")
            data = response.json()
            assert data["connected"] is True

    def test_twitch_status_with_mocked_connected_client(self):
        """Should return connected Twitch status."""
        from k2deck.web.routes.integrations import IntegrationStatus

        mock_status = IntegrationStatus(
            name="twitch",
            available=True,
            connected=True,
            status="connected",
        )

        with patch(
            "k2deck.web.routes.integrations._get_twitch_status",
            return_value=mock_status,
        ):
            response = self.client.get("/api/integrations/twitch/status")
            data = response.json()
            assert data["connected"] is True

    def test_obs_connect_success(self):
        """Should connect to OBS with mocked client."""
        from k2deck.web.routes.integrations import IntegrationStatus

        mock_status = IntegrationStatus(
            name="obs",
            available=True,
            connected=True,
            status="connected",
        )

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.connect.return_value = True

        with patch(
            "k2deck.web.routes.integrations._get_obs_status", return_value=mock_status
        ):
            with patch(
                "k2deck.core.obs_client.get_obs_client",
                return_value=mock_client,
            ):
                response = self.client.post(
                    "/api/integrations/obs/connect",
                    json={"host": "localhost", "port": 4455},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["connected"] is True

    def test_obs_connect_failure(self):
        """Should return error on OBS connect failure."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.connect.return_value = False
        mock_client.last_error = "Connection refused"

        with patch(
            "k2deck.core.obs_client.get_obs_client",
            return_value=mock_client,
        ):
            response = self.client.post("/api/integrations/obs/connect")
            assert response.status_code == 500

    def test_obs_disconnect(self):
        """Should disconnect from OBS."""
        from k2deck.web.routes.integrations import IntegrationStatus

        mock_status = IntegrationStatus(
            name="obs",
            available=True,
            connected=False,
            status="disconnected",
        )

        mock_client = MagicMock()

        with patch(
            "k2deck.web.routes.integrations._get_obs_status", return_value=mock_status
        ):
            with patch(
                "k2deck.core.obs_client.get_obs_client",
                return_value=mock_client,
            ):
                response = self.client.post("/api/integrations/obs/disconnect")
                assert response.status_code == 200
                mock_client.disconnect.assert_called_once()


class TestIntegrationStatusHelperInternals:
    """Test _get_*_status helper functions by patching at the client module level."""

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

    # --- OBS internal paths ---

    def test_obs_status_connected_via_client(self):
        """Should return connected status from real _get_obs_status logic."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True
        mock_client.get_scenes.return_value = ["Scene 1", "Scene 2"]

        with patch("k2deck.core.obs_client.get_obs_client", return_value=mock_client):
            response = self.client.get("/api/integrations/obs/status")
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["status"] == "connected"
            assert "scenes" in data["details"]

    def test_obs_status_disconnected_via_client(self):
        """Should return disconnected status from real _get_obs_status logic."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = False
        mock_client.last_error = "Connection refused"

        with patch("k2deck.core.obs_client.get_obs_client", return_value=mock_client):
            response = self.client.get("/api/integrations/obs/status")
            data = response.json()
            assert data["connected"] is False
            assert data["status"] == "disconnected"
            assert data["error"] == "Connection refused"

    def test_obs_status_exception(self):
        """Should handle exception in _get_obs_status."""
        with patch(
            "k2deck.core.obs_client.get_obs_client",
            side_effect=Exception("import error"),
        ):
            response = self.client.get("/api/integrations/obs/status")
            data = response.json()
            assert data["status"] == "error"
            assert "import error" in data["error"]

    # --- Spotify internal paths ---

    def test_spotify_status_connected_via_client(self):
        """Should return connected Spotify status from real logic."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_authenticated = True
        mock_client.get_current_user.return_value = "testuser"

        # get_spotify_client doesn't exist in real module, so create a fake module
        fake_module = MagicMock()
        fake_module.get_spotify_client = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"k2deck.core.spotify_client": fake_module}):
            response = self.client.get("/api/integrations/spotify/status")
            data = response.json()
            assert data["connected"] is True
            assert data["details"]["user"] == "testuser"

    def test_spotify_status_disconnected_via_client(self):
        """Should return disconnected Spotify status."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_authenticated = False

        fake_module = MagicMock()
        fake_module.get_spotify_client = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"k2deck.core.spotify_client": fake_module}):
            response = self.client.get("/api/integrations/spotify/status")
            data = response.json()
            assert data["connected"] is False
            assert data["status"] == "disconnected"

    def test_spotify_status_exception(self):
        """Should handle general exception in _get_spotify_status."""
        fake_module = MagicMock()
        fake_module.get_spotify_client = MagicMock(side_effect=RuntimeError("crash"))

        with patch.dict(sys.modules, {"k2deck.core.spotify_client": fake_module}):
            response = self.client.get("/api/integrations/spotify/status")
            data = response.json()
            assert data["status"] == "error"

    # --- Twitch internal paths ---

    def test_twitch_status_connected_via_client(self):
        """Should return connected Twitch status from real logic."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = True

        with patch(
            "k2deck.core.twitch_client.get_twitch_client", return_value=mock_client
        ):
            response = self.client.get("/api/integrations/twitch/status")
            data = response.json()
            assert data["connected"] is True

    def test_twitch_status_disconnected_via_client(self):
        """Should return disconnected Twitch status."""
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.is_connected = False

        with patch(
            "k2deck.core.twitch_client.get_twitch_client", return_value=mock_client
        ):
            response = self.client.get("/api/integrations/twitch/status")
            data = response.json()
            assert data["connected"] is False
            assert data["status"] == "disconnected"

    def test_twitch_status_exception(self):
        """Should handle exception in _get_twitch_status."""
        with patch(
            "k2deck.core.twitch_client.get_twitch_client",
            side_effect=Exception("twitch error"),
        ):
            response = self.client.get("/api/integrations/twitch/status")
            data = response.json()
            assert data["status"] == "error"

    # --- Connect/Disconnect additional paths ---

    def test_obs_connect_unavailable(self):
        """Should return 400 when OBS library not available."""
        mock_client = MagicMock()
        mock_client.is_available = False

        with patch("k2deck.core.obs_client.get_obs_client", return_value=mock_client):
            response = self.client.post("/api/integrations/obs/connect")
            assert response.status_code == 400

    def test_obs_connect_exception(self):
        """Should return 500 on unexpected OBS connect error."""
        with patch(
            "k2deck.core.obs_client.get_obs_client", side_effect=Exception("unexpected")
        ):
            response = self.client.post("/api/integrations/obs/connect")
            assert response.status_code == 500

    def test_spotify_connect_not_implemented(self):
        """Should return 501 for Spotify connect."""
        response = self.client.post("/api/integrations/spotify/connect")
        assert response.status_code == 501

    def test_twitch_connect_not_implemented(self):
        """Should return 501 for Twitch connect."""
        response = self.client.post("/api/integrations/twitch/connect")
        assert response.status_code == 501

    def test_spotify_disconnect_not_implemented(self):
        """Should return 501 for Spotify disconnect."""
        response = self.client.post("/api/integrations/spotify/disconnect")
        assert response.status_code == 501

    def test_twitch_disconnect_not_implemented(self):
        """Should return 501 for Twitch disconnect."""
        response = self.client.post("/api/integrations/twitch/disconnect")
        assert response.status_code == 501

    def test_obs_disconnect_exception(self):
        """Should return 500 on OBS disconnect failure."""
        with patch(
            "k2deck.core.obs_client.get_obs_client",
            side_effect=Exception("disconnect fail"),
        ):
            response = self.client.post("/api/integrations/obs/disconnect")
            assert response.status_code == 500
