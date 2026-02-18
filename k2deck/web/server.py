"""FastAPI Web Server - K2 Deck Web UI Backend.

Provides REST API and WebSocket endpoints for the K2 Deck configuration UI.
Listens only on localhost (127.0.0.1) for security.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from k2deck.core.analog_state import get_analog_state_manager
from k2deck.web.routes import config, integrations, k2, profiles
from k2deck.web.websocket.manager import (
    EventType,
    get_connection_manager,
    send_analog_state,
    set_server_loop,
)

logger = logging.getLogger(__name__)

# Default port (K-2 = 8420)
DEFAULT_PORT = 8420

# Frontend static files directory
FRONTEND_DIR = Path(__file__).parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Startup:
    - Register server's event loop for thread-safe WebSocket broadcasts
    - Register analog state callback for WebSocket broadcast
    - Log server start

    Shutdown:
    - Clean up resources
    """
    logger.info("K2 Deck Web UI starting...")

    # Register server's event loop for thread-safe broadcasts from MIDI thread
    set_server_loop(asyncio.get_running_loop())

    # Register analog state callback to broadcast changes
    analog_manager = get_analog_state_manager()

    def on_analog_change(cc: int, value: int) -> None:
        """Broadcast analog changes to WebSocket clients."""
        from k2deck.web.websocket.manager import broadcast_analog_change

        broadcast_analog_change(cc, value)

    analog_manager.register_callback(on_analog_change)

    yield

    # Cleanup
    analog_manager.unregister_callback(on_analog_change)
    logger.info("K2 Deck Web UI stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="K2 Deck",
        description="Xone:K2 MIDI Controller Configuration API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS - allow localhost only (for development)
    # Use regex to match any localhost port (wildcards don't work in allow_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(config.router, prefix="/api/config", tags=["config"])
    app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
    app.include_router(k2.router, prefix="/api/k2", tags=["k2"])
    app.include_router(
        integrations.router, prefix="/api/integrations", tags=["integrations"]
    )

    # WebSocket endpoint
    @app.websocket("/ws/events")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time events.

        Sends:
        - midi_event: MIDI messages from K2
        - led_change: LED state changes
        - layer_change: Layer changes
        - folder_change: Folder navigation
        - analog_change: Fader/pot movements
        - connection_change: K2 connection status
        - integration_change: OBS/Spotify/Twitch status
        - profile_change: Profile changes

        Receives:
        - set_led: Change LED color
        - trigger_action: Execute an action
        """
        manager = get_connection_manager()
        await manager.connect(websocket)

        try:
            # Send initial analog state
            analog_manager = get_analog_state_manager()
            await send_analog_state(websocket, analog_manager.get_all())

            # Listen for client messages
            while True:
                data = await websocket.receive_json()
                handle_client_message(data, websocket)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("WebSocket error: %s", e)
        finally:
            await manager.disconnect(websocket)

    # Serve static frontend files (if built)
    if FRONTEND_DIR.exists():
        app.mount(
            "/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend"
        )
        logger.info("Serving frontend from %s", FRONTEND_DIR)

    return app


def handle_client_message(data: dict, websocket: WebSocket) -> None:
    """Handle incoming WebSocket message from client.

    Synchronous handler - all operations are sync.

    Args:
        data: Parsed JSON message.
        websocket: Client connection (unused, kept for future async needs).
    """
    event_type = data.get("type")
    event_data = data.get("data", {})

    if event_type == EventType.SET_LED.value:
        # Set LED color
        note = event_data.get("note")
        color = event_data.get("color")

        if note is not None:
            from k2deck.feedback.led_manager import get_led_manager

            led_manager = get_led_manager()
            if color:
                led_manager.set_led(note, color)
            else:
                led_manager.set_led_off(note)
            logger.debug("WebSocket: Set LED %d to %s", note, color)

    elif event_type == EventType.TRIGGER_ACTION.value:
        # Trigger an action (for testing)
        action_type = event_data.get("action")
        action_config = event_data.get("config", {})

        if action_type:
            from k2deck.core.action_factory import create_action
            from k2deck.core.midi_listener import MidiEvent

            try:
                action = create_action({"action": action_type, **action_config})
                if action:
                    # Create a fake note_on event
                    event = MidiEvent(
                        type="note_on",
                        channel=16,
                        note=0,
                        cc=None,
                        value=127,
                        timestamp=0.0,
                    )
                    action.execute(event)
                    logger.info("WebSocket: Triggered action %s", action_type)
            except Exception as e:
                logger.error("WebSocket: Failed to trigger action: %s", e)

    else:
        logger.warning("WebSocket: Unknown message type: %s", event_type)


# Create the app instance
app = create_app()


def run_server(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    """Run the web server.

    Args:
        host: Host to bind to (default: localhost only).
        port: Port to listen on (default: 8420).
    """
    import uvicorn

    logger.info("Starting K2 Deck Web UI on http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_server_background(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    """Run the web server in a background thread.

    Args:
        host: Host to bind to.
        port: Port to listen on.
    """
    import threading

    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    logger.info("K2 Deck Web UI running in background on http://%s:%d", host, port)
