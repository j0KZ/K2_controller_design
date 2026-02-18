"""Extended tests for server.py - lifespan, handle_client_message."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from k2deck.core.analog_state import AnalogStateManager


class TestHandleClientMessage:
    """Test handle_client_message function."""

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

    def test_websocket_unknown_message_type(self):
        """Should handle unknown message types gracefully."""
        with self.client.websocket_connect("/ws/events") as websocket:
            # Receive initial analog state
            websocket.receive_json()

            # Send unknown message type
            websocket.send_json({"type": "unknown_type", "data": {}})

            import time

            time.sleep(0.1)

        # No crash = success

    def test_websocket_trigger_action(self):
        """Should handle trigger_action message."""
        with self.client.websocket_connect("/ws/events") as websocket:
            websocket.receive_json()

            # Send trigger_action — will fail to import action_factory
            # but should not crash the WebSocket
            websocket.send_json(
                {
                    "type": "trigger_action",
                    "data": {"action": "hotkey", "config": {"keys": ["f1"]}},
                }
            )

            import time

            time.sleep(0.1)

        # No crash = success

    def test_websocket_set_led_without_manager(self):
        """Should handle set_led when LED manager not initialized."""
        with self.client.websocket_connect("/ws/events") as websocket:
            websocket.receive_json()

            # Send set_led — will try to import get_led_manager
            # which may raise RuntimeError if not initialized
            websocket.send_json(
                {
                    "type": "set_led",
                    "data": {"note": 36, "color": "green"},
                }
            )

            import time

            time.sleep(0.1)

        # No crash = success

    def test_websocket_set_led_note_none(self):
        """Should handle set_led with missing note."""
        with self.client.websocket_connect("/ws/events") as websocket:
            websocket.receive_json()

            websocket.send_json(
                {
                    "type": "set_led",
                    "data": {},  # no note
                }
            )

            import time

            time.sleep(0.1)


class TestServerLifespan:
    """Test server lifespan events."""

    def test_create_app_returns_fastapi(self):
        """Should create a FastAPI app."""
        AnalogStateManager._instance = None

        with patch("k2deck.web.routes.config.CONFIG_DIR") as mock_dir:
            with patch("k2deck.web.routes.profiles.CONFIG_DIR"):
                mock_dir.__truediv__ = MagicMock()
                from k2deck.web.server import create_app

                app = create_app()
                assert app is not None
                assert app.title == "K2 Deck"

    def test_app_includes_routes(self):
        """Should include all route prefixes."""
        AnalogStateManager._instance = None

        with patch("k2deck.web.routes.config.CONFIG_DIR") as mock_dir:
            with patch("k2deck.web.routes.profiles.CONFIG_DIR"):
                mock_dir.__truediv__ = MagicMock()
                from k2deck.web.server import create_app

                app = create_app()
                route_paths = [r.path for r in app.routes]

                # Check key routes exist
                assert any("/api/config" in p for p in route_paths)
                assert any("/api/k2" in p for p in route_paths)
                assert any("/ws/events" in p for p in route_paths)

    def test_lifespan_registers_analog_callback(self):
        """Should register analog state callback during lifespan."""
        AnalogStateManager._instance = None

        config_dir = Path(__file__).parent.parent / "config"
        with patch("k2deck.web.routes.config.CONFIG_DIR", config_dir):
            with patch("k2deck.web.routes.profiles.CONFIG_DIR", config_dir):
                from k2deck.web.server import create_app

                app = create_app()
                # TestClient triggers lifespan
                with TestClient(app) as client:
                    # Lifespan runs — verify analog manager has callback
                    analog_manager = AnalogStateManager()
                    assert len(analog_manager._callbacks) > 0

                    # Verify API works
                    response = client.get("/api/k2/layout")
                    assert response.status_code == 200


class TestHandleClientMessageDirect:
    """Test handle_client_message function directly for deeper coverage."""

    def test_trigger_action_with_successful_create(self):
        """Should execute action when create_action returns non-None."""
        from k2deck.web.server import handle_client_message

        mock_action = MagicMock()
        mock_ws = MagicMock()

        with patch(
            "k2deck.core.action_factory.create_action", return_value=mock_action
        ):
            handle_client_message(
                {
                    "type": "trigger_action",
                    "data": {"action": "hotkey", "config": {"keys": ["f1"]}},
                },
                mock_ws,
            )

        # create_action is called with positional args: action_type, action_config
        mock_action.execute.assert_called_once()

    def test_trigger_action_create_returns_none(self):
        """Should handle None from create_action gracefully."""
        from k2deck.web.server import handle_client_message

        mock_ws = MagicMock()

        with patch("k2deck.core.action_factory.create_action", return_value=None):
            handle_client_message(
                {"type": "trigger_action", "data": {"action": "bad_action"}},
                mock_ws,
            )
        # No crash = success

    def test_trigger_action_exception(self):
        """Should handle exception during action execution."""
        from k2deck.web.server import handle_client_message

        mock_action = MagicMock()
        mock_action.execute.side_effect = Exception("action failed")
        mock_ws = MagicMock()

        with patch(
            "k2deck.core.action_factory.create_action", return_value=mock_action
        ):
            handle_client_message(
                {"type": "trigger_action", "data": {"action": "hotkey", "config": {}}},
                mock_ws,
            )
        # No crash = success

    def test_trigger_action_missing_action_type(self):
        """Should skip when action type is missing."""
        from k2deck.web.server import handle_client_message

        mock_ws = MagicMock()
        handle_client_message(
            {"type": "trigger_action", "data": {}},
            mock_ws,
        )
        # No crash = success

    def test_set_led_with_color(self):
        """Should set LED via led_manager when color provided."""
        from k2deck.web.server import handle_client_message

        mock_manager = MagicMock()
        mock_ws = MagicMock()

        with patch(
            "k2deck.feedback.led_manager.get_led_manager", return_value=mock_manager
        ):
            handle_client_message(
                {"type": "set_led", "data": {"note": 36, "color": "green"}},
                mock_ws,
            )

        mock_manager.set_led.assert_called_once_with(36, "green")

    def test_set_led_without_color(self):
        """Should turn off LED when no color provided."""
        from k2deck.web.server import handle_client_message

        mock_manager = MagicMock()
        mock_ws = MagicMock()

        with patch(
            "k2deck.feedback.led_manager.get_led_manager", return_value=mock_manager
        ):
            handle_client_message(
                {"type": "set_led", "data": {"note": 36}},
                mock_ws,
            )

        mock_manager.set_led_off.assert_called_once_with(36)


class TestRunServer:
    """Test run_server and run_server_background functions."""

    def test_run_server(self):
        """Should call uvicorn.run with correct params."""
        import uvicorn

        with patch.object(uvicorn, "run") as mock_run:
            from k2deck.web.server import run_server

            run_server("127.0.0.1", 8420)
            mock_run.assert_called_once()

    def test_run_server_background(self):
        """Should start uvicorn server in background thread."""
        import threading

        import uvicorn

        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()

        with patch.object(uvicorn, "Config"):
            with patch.object(uvicorn, "Server", return_value=mock_server_instance):
                with patch.object(
                    threading, "Thread", return_value=mock_thread_instance
                ) as mock_thread:
                    from k2deck.web.server import run_server_background

                    run_server_background("127.0.0.1", 8420)

                    mock_thread.assert_called_once()
                    mock_thread_instance.start.assert_called_once()
