"""Tests for k2deck.web.routes.k2 — Trigger and Timer endpoints."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from k2deck.web.server import app


class TestTriggerEndpoint:
    def setup_method(self):
        """Create test client."""
        self.client = TestClient(app)

    @patch("k2deck.core.action_factory.create_action")
    def test_trigger_valid_action(self, mock_create):
        """POST /api/k2/trigger with valid action returns 200."""
        mock_action = MagicMock()
        mock_create.return_value = mock_action

        resp = self.client.post(
            "/api/k2/trigger",
            json={"action": "timer_start", "config": {"name": "test", "seconds": 60}},
        )

        assert resp.status_code == 200
        assert "timer_start" in resp.json()["message"]
        mock_create.assert_called_once_with(
            {"action": "timer_start", "name": "test", "seconds": 60}
        )
        mock_action.execute.assert_called_once()

    @patch("k2deck.core.action_factory.create_action", return_value=None)
    def test_trigger_unknown_action(self, mock_create):
        """POST /api/k2/trigger with unknown action returns 400."""
        resp = self.client.post(
            "/api/k2/trigger",
            json={"action": "bogus_action"},
        )
        assert resp.status_code == 400
        assert "Unknown action type" in resp.json()["detail"]

    @patch("k2deck.core.action_factory.create_action")
    def test_trigger_empty_config(self, mock_create):
        """POST /api/k2/trigger with no config defaults to empty dict."""
        mock_action = MagicMock()
        mock_create.return_value = mock_action

        resp = self.client.post(
            "/api/k2/trigger",
            json={"action": "hotkey"},
        )

        assert resp.status_code == 200
        mock_create.assert_called_once_with({"action": "hotkey"})

    @patch("k2deck.core.action_factory.create_action")
    def test_trigger_action_error_500(self, mock_create):
        """POST /api/k2/trigger returns 500 if action.execute raises."""
        mock_action = MagicMock()
        mock_action.execute.side_effect = RuntimeError("boom")
        mock_create.return_value = mock_action

        resp = self.client.post(
            "/api/k2/trigger",
            json={"action": "hotkey", "config": {"keys": ["f1"]}},
        )
        assert resp.status_code == 500

    def test_trigger_missing_action_field(self):
        """POST /api/k2/trigger without action field returns 422."""
        resp = self.client.post(
            "/api/k2/trigger",
            json={"config": {"name": "test"}},
        )
        assert resp.status_code == 422


class TestTimerEndpoint:
    def setup_method(self):
        """Create test client."""
        self.client = TestClient(app)

    @patch("k2deck.core.timer_manager.get_timer_manager")
    def test_get_timers_returns_status(self, mock_get_mgr):
        """GET /api/k2/timers returns timer dict."""
        mock_mgr = MagicMock()
        mock_mgr.get_all.return_value = {
            "pomodoro": {"duration": 60, "remaining": 30, "running": True}
        }
        mock_get_mgr.return_value = mock_mgr

        resp = self.client.get("/api/k2/timers")
        assert resp.status_code == 200
        data = resp.json()
        assert "pomodoro" in data
        assert data["pomodoro"]["running"] is True

    @patch("k2deck.core.timer_manager.get_timer_manager")
    def test_get_timers_empty(self, mock_get_mgr):
        """GET /api/k2/timers returns empty dict when no timers."""
        mock_mgr = MagicMock()
        mock_mgr.get_all.return_value = {}
        mock_get_mgr.return_value = mock_mgr

        resp = self.client.get("/api/k2/timers")
        assert resp.status_code == 200
        assert resp.json() == {}
