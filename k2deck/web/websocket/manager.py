"""WebSocket Connection Manager - Real-time event broadcast.

Manages WebSocket connections and broadcasts events to all connected clients.
Events include: MIDI events, LED changes, layer changes, analog changes, etc.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """WebSocket event types."""

    # Server -> Client events
    MIDI_EVENT = "midi_event"
    LED_CHANGE = "led_change"
    LAYER_CHANGE = "layer_change"
    FOLDER_CHANGE = "folder_change"
    CONNECTION_CHANGE = "connection_change"
    INTEGRATION_CHANGE = "integration_change"
    PROFILE_CHANGE = "profile_change"
    ANALOG_CHANGE = "analog_change"
    ANALOG_STATE = "analog_state"

    # Client -> Server commands
    SET_LED = "set_led"
    TRIGGER_ACTION = "trigger_action"


@dataclass
class WebSocketEvent:
    """A WebSocket event to broadcast."""

    type: EventType
    data: dict[str, Any]

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({"type": self.type.value, "data": self.data})


@dataclass
class ConnectionManager:
    """Manages WebSocket connections and broadcasts.

    Features:
    - Track all active connections
    - Broadcast events to all clients
    - Handle client commands
    - Thread-safe operations
    """

    active_connections: list[WebSocket] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected. Total: %d", len(self.active_connections)
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(
            "WebSocket client disconnected. Total: %d", len(self.active_connections)
        )

    async def broadcast(self, event: WebSocketEvent) -> None:
        """Broadcast an event to all connected clients.

        Args:
            event: The event to broadcast.
        """
        if not self.active_connections:
            return

        message = event.to_json()
        disconnected: list[WebSocket] = []

        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning("Failed to send to client: %s", e)
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)

    async def send_personal(self, websocket: WebSocket, event: WebSocketEvent) -> None:
        """Send an event to a specific client.

        Args:
            websocket: The target WebSocket connection.
            event: The event to send.
        """
        try:
            await websocket.send_text(event.to_json())
        except Exception as e:
            logger.warning("Failed to send personal message: %s", e)

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


# Global connection manager instance
_manager: ConnectionManager | None = None
# Server's event loop (set during startup for thread-safe broadcasting)
_server_loop: asyncio.AbstractEventLoop | None = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager.

    Returns:
        The ConnectionManager singleton.
    """
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


def set_server_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Store the server's event loop for thread-safe broadcasting.

    Called during server startup.

    Args:
        loop: The asyncio event loop running the FastAPI server.
    """
    global _server_loop
    _server_loop = loop
    logger.debug("Server event loop registered for WebSocket broadcasting")


# ============================================================================
# Event Helper Functions (for use from non-async code)
# ============================================================================


def broadcast_sync(event: WebSocketEvent) -> None:
    """Broadcast an event from synchronous code (thread-safe).

    Can be called from any thread (e.g., MIDI listener thread).
    Uses run_coroutine_threadsafe to safely schedule on server's loop.

    Args:
        event: The event to broadcast.
    """
    manager = get_connection_manager()

    if _server_loop is None:
        # Server not started yet, silently ignore
        logger.debug("WebSocket broadcast skipped: server loop not initialized")
        return

    if not _server_loop.is_running():
        logger.debug("WebSocket broadcast skipped: server loop not running")
        return

    # Thread-safe scheduling on the server's event loop
    try:
        future = asyncio.run_coroutine_threadsafe(
            manager.broadcast(event), _server_loop
        )
        # Don't wait for result - fire and forget
        # Add callback to log errors
        future.add_done_callback(_broadcast_error_handler)
    except Exception as e:
        logger.warning("Failed to schedule WebSocket broadcast: %s", e)


def _broadcast_error_handler(future: asyncio.Future) -> None:
    """Handle errors from async broadcast operations."""
    try:
        future.result()
    except Exception as e:
        logger.warning("WebSocket broadcast failed: %s", e)


def broadcast_midi_event(
    event_type: str, channel: int, note: int | None, cc: int | None, value: int
) -> None:
    """Broadcast a MIDI event.

    Args:
        event_type: "note_on", "note_off", or "cc".
        channel: MIDI channel.
        note: Note number (for note events).
        cc: CC number (for CC events).
        value: Velocity or CC value.
    """
    event = WebSocketEvent(
        type=EventType.MIDI_EVENT,
        data={
            "type": event_type,
            "channel": channel,
            "note": note,
            "cc": cc,
            "value": value,
        },
    )
    broadcast_sync(event)


def broadcast_led_change(note: int, color: str | None, on: bool) -> None:
    """Broadcast an LED state change.

    Args:
        note: Base note of the LED.
        color: Color name ("red", "amber", "green") or None if off.
        on: Whether LED is on.
    """
    event = WebSocketEvent(
        type=EventType.LED_CHANGE,
        data={"note": note, "color": color, "on": on},
    )
    broadcast_sync(event)


def broadcast_layer_change(layer: int, previous: int) -> None:
    """Broadcast a layer change.

    Args:
        layer: New layer number (1-based).
        previous: Previous layer number.
    """
    event = WebSocketEvent(
        type=EventType.LAYER_CHANGE,
        data={"layer": layer, "previous": previous},
    )
    broadcast_sync(event)


def broadcast_folder_change(folder: str | None, previous: str | None) -> None:
    """Broadcast a folder change.

    Args:
        folder: New folder name or None for root.
        previous: Previous folder name or None.
    """
    event = WebSocketEvent(
        type=EventType.FOLDER_CHANGE,
        data={"folder": folder, "previous": previous},
    )
    broadcast_sync(event)


def broadcast_connection_change(connected: bool, port: str | None) -> None:
    """Broadcast K2 connection state change.

    Args:
        connected: Whether K2 is connected.
        port: MIDI port name or None.
    """
    event = WebSocketEvent(
        type=EventType.CONNECTION_CHANGE,
        data={"connected": connected, "port": port},
    )
    broadcast_sync(event)


def broadcast_integration_change(name: str, status: str) -> None:
    """Broadcast integration status change.

    Args:
        name: Integration name (obs, spotify, twitch).
        status: Status string (connected, disconnected, error).
    """
    event = WebSocketEvent(
        type=EventType.INTEGRATION_CHANGE,
        data={"name": name, "status": status},
    )
    broadcast_sync(event)


def broadcast_profile_change(profile: str, previous: str | None) -> None:
    """Broadcast profile change.

    Args:
        profile: New profile name.
        previous: Previous profile name or None.
    """
    event = WebSocketEvent(
        type=EventType.PROFILE_CHANGE,
        data={"profile": profile, "previous": previous},
    )
    broadcast_sync(event)


def broadcast_analog_change(cc: int, value: int, control_id: str = "") -> None:
    """Broadcast analog control value change.

    Args:
        cc: CC number.
        value: New value (0-127).
        control_id: Control identifier (e.g., "F1", "P3").
    """
    event = WebSocketEvent(
        type=EventType.ANALOG_CHANGE,
        data={"cc": cc, "value": value, "control_id": control_id},
    )
    broadcast_sync(event)


async def send_analog_state(websocket: WebSocket, positions: dict[int, int]) -> None:
    """Send initial analog state to a newly connected client.

    Args:
        websocket: The client connection.
        positions: Dict of cc -> value for all analog controls.
    """
    manager = get_connection_manager()
    controls = [{"cc": cc, "value": value} for cc, value in positions.items()]

    event = WebSocketEvent(
        type=EventType.ANALOG_STATE,
        data={"controls": controls},
    )
    await manager.send_personal(websocket, event)
