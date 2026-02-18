"""OBS WebSocket Client Manager - Singleton with reconnect logic.

Manages connection to OBS Studio via WebSocket v5 API.
Handles lazy initialization, reconnection, and error recovery.
"""

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# Optional dependency - will be None if not installed
try:
    import obsws_python as obs
    from obsws_python.error import OBSSDKError, OBSSDKRequestError, OBSSDKTimeoutError

    HAS_OBSWS = True
except ImportError:
    obs = None
    OBSSDKError = Exception
    OBSSDKRequestError = Exception
    OBSSDKTimeoutError = Exception
    HAS_OBSWS = False


class OBSClientManager:
    """Singleton manager for OBS WebSocket connection.

    Features:
    - Lazy initialization (connects on first use)
    - Automatic reconnection on failure
    - Thread-safe connection management
    - Configurable connection parameters
    """

    _instance: "OBSClientManager | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "OBSClientManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the manager (only runs once due to singleton)."""
        if self._initialized:
            return

        self._client: Any | None = None
        self._host = "localhost"
        self._port = 4455
        self._password = ""
        self._timeout = 3
        self._connected = False
        self._last_error: str | None = None
        self._reconnect_interval = 5.0  # seconds
        self._last_connect_attempt = 0.0
        self._connection_lock = threading.Lock()
        self._initialized = True

    def configure(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
        timeout: int = 3,
    ) -> None:
        """Configure connection parameters.

        Args:
            host: OBS WebSocket host.
            port: OBS WebSocket port.
            password: OBS WebSocket password (empty if not set).
            timeout: Connection timeout in seconds.
        """
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        logger.info("OBS configured: %s:%d", host, port)

    @property
    def is_available(self) -> bool:
        """Check if obsws-python library is installed."""
        return HAS_OBSWS

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to OBS."""
        return self._connected and self._client is not None

    @property
    def last_error(self) -> str | None:
        """Get the last connection error message."""
        return self._last_error

    def connect(self) -> bool:
        """Establish connection to OBS.

        Returns:
            True if connected successfully, False otherwise.
        """
        if not HAS_OBSWS:
            self._last_error = (
                "obsws-python not installed. Run: pip install obsws-python"
            )
            logger.warning(self._last_error)
            return False

        with self._connection_lock:
            # Rate limit connection attempts
            now = time.time()
            if now - self._last_connect_attempt < self._reconnect_interval:
                return self._connected
            self._last_connect_attempt = now

            try:
                self._client = obs.ReqClient(
                    host=self._host,
                    port=self._port,
                    password=self._password,
                    timeout=self._timeout,
                )
                # Test connection
                version = self._client.get_version()
                self._connected = True
                self._last_error = None
                logger.info(
                    "Connected to OBS %s (WebSocket %s)",
                    version.obs_version,
                    version.obs_web_socket_version,
                )
                return True

            except OBSSDKTimeoutError:
                self._last_error = (
                    f"Connection timeout to OBS at {self._host}:{self._port}"
                )
                logger.warning(self._last_error)
            except OBSSDKError as e:
                self._last_error = f"OBS connection failed: {e}"
                logger.warning(self._last_error)
            except Exception as e:
                self._last_error = f"Unexpected error connecting to OBS: {e}"
                logger.error(self._last_error)

            self._client = None
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from OBS."""
        with self._connection_lock:
            if self._client is not None:
                try:
                    self._client.disconnect()
                except Exception:
                    pass  # Ignore errors during disconnect
                self._client = None
            self._connected = False
            logger.info("Disconnected from OBS")

    def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection, reconnecting if needed.

        Returns:
            True if connected, False otherwise.
        """
        if self._connected and self._client is not None:
            return True
        return self.connect()

    def get_client(self) -> Any | None:
        """Get the OBS client, connecting if needed.

        Returns:
            The obsws-python ReqClient, or None if not connected.
        """
        if self._ensure_connected():
            return self._client
        return None

    # =========================================================================
    # High-level OBS operations (with auto-reconnect)
    # =========================================================================

    def set_scene(self, scene_name: str) -> bool:
        """Switch to a specific scene.

        Args:
            scene_name: Name of the scene to switch to.

        Returns:
            True if successful, False otherwise.
        """
        client = self.get_client()
        if not client:
            return False

        try:
            client.set_current_program_scene(scene_name)
            logger.info("OBS: Switched to scene '%s'", scene_name)
            return True
        except OBSSDKRequestError as e:
            logger.warning("OBS: Failed to switch scene - %s", e)
            return False
        except (OBSSDKTimeoutError, OBSSDKError) as e:
            logger.warning("OBS: Connection error - %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.warning("OBS: Unexpected error switching scene - %s", e)
            return False

    def toggle_source_visibility(
        self, scene_name: str, source_name: str, visible: bool | None = None
    ) -> bool:
        """Toggle or set source visibility.

        Args:
            scene_name: Name of the scene containing the source.
            source_name: Name of the source/item.
            visible: True to show, False to hide, None to toggle.

        Returns:
            True if successful, False otherwise.
        """
        client = self.get_client()
        if not client:
            return False

        try:
            # Get the scene item ID
            items = client.get_scene_item_list(scene_name)
            item_id = None
            for item in items.scene_items:
                if item.get("sourceName") == source_name:
                    item_id = item.get("sceneItemId")
                    break

            if item_id is None:
                logger.warning(
                    "OBS: Source '%s' not found in scene '%s'", source_name, scene_name
                )
                return False

            # Get current visibility if toggling
            if visible is None:
                current = client.get_scene_item_enabled(scene_name, item_id)
                visible = not current.scene_item_enabled

            # Set visibility
            client.set_scene_item_enabled(scene_name, item_id, visible)
            state = "visible" if visible else "hidden"
            logger.info("OBS: Source '%s' is now %s", source_name, state)
            return True

        except OBSSDKRequestError as e:
            logger.warning("OBS: Failed to toggle source - %s", e)
            return False
        except (OBSSDKTimeoutError, OBSSDKError) as e:
            logger.warning("OBS: Connection error - %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.warning("OBS: Unexpected error toggling source - %s", e)
            return False

    def toggle_stream(self, action: str = "toggle") -> bool:
        """Control streaming.

        Args:
            action: "start", "stop", or "toggle".

        Returns:
            True if successful, False otherwise.
        """
        client = self.get_client()
        if not client:
            return False

        try:
            if action == "toggle":
                result = client.toggle_stream()
                state = "started" if result.output_active else "stopped"
            elif action == "start":
                client.start_stream()
                state = "started"
            elif action == "stop":
                client.stop_stream()
                state = "stopped"
            else:
                logger.warning("OBS: Invalid stream action '%s'", action)
                return False

            logger.info("OBS: Stream %s", state)
            return True

        except OBSSDKRequestError as e:
            logger.warning("OBS: Failed to control stream - %s", e)
            return False
        except (OBSSDKTimeoutError, OBSSDKError) as e:
            logger.warning("OBS: Connection error - %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.warning("OBS: Unexpected error controlling stream - %s", e)
            return False

    def toggle_record(self, action: str = "toggle") -> bool:
        """Control recording.

        Args:
            action: "start", "stop", "toggle", or "pause".

        Returns:
            True if successful, False otherwise.
        """
        client = self.get_client()
        if not client:
            return False

        try:
            if action == "toggle":
                result = client.toggle_record()
                state = "started" if result.output_active else "stopped"
            elif action == "start":
                client.start_record()
                state = "started"
            elif action == "stop":
                client.stop_record()
                state = "stopped"
            elif action == "pause":
                client.toggle_record_pause()
                state = "pause toggled"
            else:
                logger.warning("OBS: Invalid record action '%s'", action)
                return False

            logger.info("OBS: Recording %s", state)
            return True

        except OBSSDKRequestError as e:
            logger.warning("OBS: Failed to control recording - %s", e)
            return False
        except (OBSSDKTimeoutError, OBSSDKError) as e:
            logger.warning("OBS: Connection error - %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.warning("OBS: Unexpected error controlling recording - %s", e)
            return False

    def toggle_mute(self, input_name: str, muted: bool | None = None) -> bool:
        """Toggle or set input mute state.

        Args:
            input_name: Name of the audio input.
            muted: True to mute, False to unmute, None to toggle.

        Returns:
            True if successful, False otherwise.
        """
        client = self.get_client()
        if not client:
            return False

        try:
            if muted is None:
                result = client.toggle_input_mute(input_name)
                state = "muted" if result.input_muted else "unmuted"
            else:
                client.set_input_mute(input_name, muted)
                state = "muted" if muted else "unmuted"

            logger.info("OBS: Input '%s' %s", input_name, state)
            return True

        except OBSSDKRequestError as e:
            logger.warning("OBS: Failed to toggle mute - %s", e)
            return False
        except (OBSSDKTimeoutError, OBSSDKError) as e:
            logger.warning("OBS: Connection error - %s", e)
            self._connected = False
            return False
        except Exception as e:
            logger.warning("OBS: Unexpected error toggling mute - %s", e)
            return False

    def get_scenes(self) -> list[str]:
        """Get list of available scenes.

        Returns:
            List of scene names.
        """
        client = self.get_client()
        if not client:
            return []

        try:
            result = client.get_scene_list()
            return [scene["sceneName"] for scene in result.scenes]
        except Exception as e:
            logger.warning("OBS: Failed to get scenes - %s", e)
            return []


# Module-level singleton accessor
def get_obs_client() -> OBSClientManager:
    """Get the OBS client manager singleton.

    Returns:
        The OBSClientManager instance.
    """
    return OBSClientManager()
