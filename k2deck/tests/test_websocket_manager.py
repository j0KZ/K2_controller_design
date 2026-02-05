"""Tests for WebSocket Connection Manager."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from k2deck.web.websocket.manager import (
    ConnectionManager,
    EventType,
    WebSocketEvent,
    _broadcast_error_handler,
    broadcast_analog_change,
    broadcast_connection_change,
    broadcast_folder_change,
    broadcast_integration_change,
    broadcast_layer_change,
    broadcast_led_change,
    broadcast_midi_event,
    broadcast_profile_change,
    broadcast_sync,
    get_connection_manager,
    send_analog_state,
    set_server_loop,
)


class TestEventType:
    """Test EventType enum."""

    def test_event_types_exist(self):
        """All expected event types should exist."""
        assert EventType.MIDI_EVENT == "midi_event"
        assert EventType.LED_CHANGE == "led_change"
        assert EventType.LAYER_CHANGE == "layer_change"
        assert EventType.FOLDER_CHANGE == "folder_change"
        assert EventType.CONNECTION_CHANGE == "connection_change"
        assert EventType.INTEGRATION_CHANGE == "integration_change"
        assert EventType.PROFILE_CHANGE == "profile_change"
        assert EventType.ANALOG_CHANGE == "analog_change"
        assert EventType.ANALOG_STATE == "analog_state"
        assert EventType.SET_LED == "set_led"
        assert EventType.TRIGGER_ACTION == "trigger_action"


class TestWebSocketEvent:
    """Test WebSocketEvent dataclass."""

    def test_to_json(self):
        """Should serialize to JSON string."""
        event = WebSocketEvent(
            type=EventType.MIDI_EVENT,
            data={"type": "note_on", "channel": 16, "note": 36, "value": 127},
        )
        result = json.loads(event.to_json())

        assert result["type"] == "midi_event"
        assert result["data"]["note"] == 36
        assert result["data"]["value"] == 127

    def test_to_json_empty_data(self):
        """Should handle empty data."""
        event = WebSocketEvent(type=EventType.LED_CHANGE, data={})
        result = json.loads(event.to_json())

        assert result["type"] == "led_change"
        assert result["data"] == {}


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect(self, manager):
        """Should accept and track connection."""
        ws = AsyncMock()
        await manager.connect(ws)

        assert ws.accept.called
        assert ws in manager.active_connections
        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_connect_multiple(self, manager):
        """Should track multiple connections."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)

        assert manager.connection_count == 2

    @pytest.mark.asyncio
    async def test_disconnect(self, manager):
        """Should remove connection."""
        ws = AsyncMock()
        await manager.connect(ws)
        await manager.disconnect(ws)

        assert ws not in manager.active_connections
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self, manager):
        """Should handle disconnecting non-connected socket."""
        ws = AsyncMock()
        # Should not raise
        await manager.disconnect(ws)
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Should send to all connected clients."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)

        event = WebSocketEvent(
            type=EventType.MIDI_EVENT,
            data={"type": "note_on", "note": 36},
        )
        await manager.broadcast(event)

        assert ws1.send_text.called
        assert ws2.send_text.called

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self, manager):
        """Should return early with no connections."""
        event = WebSocketEvent(type=EventType.MIDI_EVENT, data={})
        # Should not raise
        await manager.broadcast(event)

    @pytest.mark.asyncio
    async def test_broadcast_removes_failed_clients(self, manager):
        """Should remove clients that fail to receive."""
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("Connection closed")

        await manager.connect(ws_good)
        await manager.connect(ws_bad)

        event = WebSocketEvent(type=EventType.MIDI_EVENT, data={})
        await manager.broadcast(event)

        # Bad client should be removed
        assert ws_bad not in manager.active_connections
        assert ws_good in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_personal(self, manager):
        """Should send to specific client."""
        ws = AsyncMock()
        await manager.connect(ws)

        event = WebSocketEvent(
            type=EventType.ANALOG_STATE,
            data={"controls": [{"cc": 16, "value": 64}]},
        )
        await manager.send_personal(ws, event)

        ws.send_text.assert_called_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"] == "analog_state"

    @pytest.mark.asyncio
    async def test_send_personal_error(self, manager):
        """Should handle send error gracefully."""
        ws = AsyncMock()
        ws.send_text.side_effect = Exception("Connection closed")

        event = WebSocketEvent(type=EventType.MIDI_EVENT, data={})
        # Should not raise
        await manager.send_personal(ws, event)

    def test_connection_count(self, manager):
        """Should return count of active connections."""
        assert manager.connection_count == 0


class TestGlobalFunctions:
    """Test module-level functions."""

    def test_get_connection_manager_singleton(self):
        """Should return same instance."""
        import k2deck.web.websocket.manager as mod

        old_manager = mod._manager
        mod._manager = None

        try:
            m1 = get_connection_manager()
            m2 = get_connection_manager()
            assert m1 is m2
        finally:
            mod._manager = old_manager

    def test_set_server_loop(self):
        """Should store event loop."""
        import k2deck.web.websocket.manager as mod

        old_loop = mod._server_loop
        mock_loop = MagicMock()

        try:
            set_server_loop(mock_loop)
            assert mod._server_loop is mock_loop
        finally:
            mod._server_loop = old_loop

    def test_broadcast_sync_no_loop(self):
        """Should skip when no server loop."""
        import k2deck.web.websocket.manager as mod

        old_loop = mod._server_loop
        mod._server_loop = None

        try:
            event = WebSocketEvent(type=EventType.MIDI_EVENT, data={})
            # Should not raise
            broadcast_sync(event)
        finally:
            mod._server_loop = old_loop

    def test_broadcast_sync_loop_not_running(self):
        """Should skip when loop not running."""
        import k2deck.web.websocket.manager as mod

        old_loop = mod._server_loop
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = False
        mod._server_loop = mock_loop

        try:
            event = WebSocketEvent(type=EventType.MIDI_EVENT, data={})
            broadcast_sync(event)
            mock_loop.is_running.assert_called()
        finally:
            mod._server_loop = old_loop

    def test_broadcast_sync_schedules_coroutine(self):
        """Should schedule broadcast on server loop."""
        import k2deck.web.websocket.manager as mod

        old_loop = mod._server_loop
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        mock_future = MagicMock()
        mock_loop.call_soon_threadsafe = MagicMock()

        # run_coroutine_threadsafe returns a future
        with patch("asyncio.run_coroutine_threadsafe", return_value=mock_future):
            mod._server_loop = mock_loop

            try:
                event = WebSocketEvent(type=EventType.MIDI_EVENT, data={})
                broadcast_sync(event)

                # Future should have error handler added
                mock_future.add_done_callback.assert_called_once()
            finally:
                mod._server_loop = old_loop

    def test_broadcast_error_handler_success(self):
        """Should handle successful future."""
        mock_future = MagicMock()
        mock_future.result.return_value = None
        # Should not raise
        _broadcast_error_handler(mock_future)

    def test_broadcast_error_handler_failure(self):
        """Should handle failed future."""
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Broadcast failed")
        # Should not raise (just logs)
        _broadcast_error_handler(mock_future)


class TestBroadcastHelpers:
    """Test broadcast helper functions."""

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_midi_event(self, mock_sync):
        """Should broadcast MIDI event."""
        broadcast_midi_event("note_on", 16, 36, None, 127)

        mock_sync.assert_called_once()
        event = mock_sync.call_args[0][0]
        assert event.type == EventType.MIDI_EVENT
        assert event.data["type"] == "note_on"
        assert event.data["channel"] == 16
        assert event.data["note"] == 36
        assert event.data["value"] == 127

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_led_change(self, mock_sync):
        """Should broadcast LED change."""
        broadcast_led_change(36, "green", True)

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.LED_CHANGE
        assert event.data["note"] == 36
        assert event.data["color"] == "green"
        assert event.data["on"] is True

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_layer_change(self, mock_sync):
        """Should broadcast layer change."""
        broadcast_layer_change(2, 1)

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.LAYER_CHANGE
        assert event.data["layer"] == 2
        assert event.data["previous"] == 1

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_folder_change(self, mock_sync):
        """Should broadcast folder change."""
        broadcast_folder_change("Streaming", None)

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.FOLDER_CHANGE
        assert event.data["folder"] == "Streaming"
        assert event.data["previous"] is None

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_connection_change(self, mock_sync):
        """Should broadcast connection change."""
        broadcast_connection_change(True, "XONE:K2")

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.CONNECTION_CHANGE
        assert event.data["connected"] is True
        assert event.data["port"] == "XONE:K2"

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_integration_change(self, mock_sync):
        """Should broadcast integration change."""
        broadcast_integration_change("obs", "connected")

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.INTEGRATION_CHANGE
        assert event.data["name"] == "obs"
        assert event.data["status"] == "connected"

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_profile_change(self, mock_sync):
        """Should broadcast profile change."""
        broadcast_profile_change("gaming", "default")

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.PROFILE_CHANGE
        assert event.data["profile"] == "gaming"
        assert event.data["previous"] == "default"

    @patch("k2deck.web.websocket.manager.broadcast_sync")
    def test_broadcast_analog_change(self, mock_sync):
        """Should broadcast analog change."""
        broadcast_analog_change(16, 100, "F1")

        event = mock_sync.call_args[0][0]
        assert event.type == EventType.ANALOG_CHANGE
        assert event.data["cc"] == 16
        assert event.data["value"] == 100
        assert event.data["control_id"] == "F1"


class TestSendAnalogState:
    """Test send_analog_state function."""

    @pytest.mark.asyncio
    async def test_send_analog_state(self):
        """Should send analog state to specific client."""
        ws = AsyncMock()
        positions = {16: 64, 17: 100, 18: 0}

        await send_analog_state(ws, positions)

        ws.send_text.assert_called_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"] == "analog_state"
        assert len(sent["data"]["controls"]) == 3

    @pytest.mark.asyncio
    async def test_send_analog_state_empty(self):
        """Should handle empty positions."""
        ws = AsyncMock()
        await send_analog_state(ws, {})

        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["data"]["controls"] == []
