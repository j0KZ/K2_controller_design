"""Twitch API client wrapper using twitchAPI.

Provides OAuth authentication and API methods for stream control.
Uses async twitchAPI with sync wrapper via ThreadPoolExecutor.
"""

import asyncio
import logging
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# Optional dependency
try:
    from twitchAPI.twitch import Twitch
    from twitchAPI.oauth import UserAuthenticator
    from twitchAPI.type import AuthScope
    HAS_TWITCH = True
except ImportError:
    HAS_TWITCH = False
    Twitch = None
    UserAuthenticator = None
    AuthScope = None

# Token storage
CONFIG_DIR = Path.home() / ".k2deck"
TOKEN_FILE = CONFIG_DIR / "twitch_tokens.json"

# Rate limiting: 1 action per second minimum
MIN_ACTION_INTERVAL = 1.0

# Required scopes
TWITCH_SCOPES = [
    "channel:manage:broadcast",    # Markers, title, game
    "clips:edit",                   # Create clips
    "channel:manage:predictions",   # Predictions
    "chat:edit",                    # Send chat messages
    "chat:read",                    # Read chat
    "user:read:chat",               # Read user chat
    "user:write:chat",              # Write user chat
]


class TwitchClient:
    """Singleton wrapper for Twitch API client.

    Handles OAuth flow, token persistence, and rate limiting.
    All async twitchAPI calls are wrapped in sync methods via ThreadPoolExecutor.
    """

    _instance: "TwitchClient | None" = None
    _lock = Lock()

    def __new__(cls) -> "TwitchClient":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_instance()
        return cls._instance

    def _init_instance(self) -> None:
        """Initialize instance (called once)."""
        self._twitch: Any = None
        self._user_id: str | None = None
        self._broadcaster_id: str | None = None
        self._client_id: str = ""
        self._client_secret: str = ""
        self._connected = False
        self._initialized = False
        self._last_action_time = 0.0
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="twitch")
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_available(self) -> bool:
        """Check if twitchAPI library is installed."""
        return HAS_TWITCH

    @property
    def is_connected(self) -> bool:
        """Check if connected to Twitch."""
        return self._connected

    def configure(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """Configure Twitch API credentials.

        Args:
            client_id: Twitch app client ID (or set TWITCH_CLIENT_ID env var)
            client_secret: Twitch app client secret (or set TWITCH_CLIENT_SECRET env var)
        """
        self._client_id = client_id or os.environ.get("TWITCH_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")

    def initialize(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> bool:
        """Initialize and authenticate with Twitch.

        Args:
            client_id: Twitch app client ID
            client_secret: Twitch app client secret

        Returns:
            True if initialization successful.
        """
        if self._initialized and self._connected:
            return True

        if not HAS_TWITCH:
            logger.warning(
                "twitchAPI not installed. Run: pip install twitchAPI"
            )
            return False

        # Configure credentials
        if client_id or client_secret:
            self.configure(client_id, client_secret)

        if not self._client_id or not self._client_secret:
            logger.warning(
                "Twitch credentials not configured. "
                "Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET environment variables."
            )
            return False

        # Run async connect in executor
        try:
            future = self._executor.submit(self._run_async, self._async_connect())
            result = future.result(timeout=60)  # 60s timeout for OAuth flow
            return result
        except Exception as e:
            logger.error("Failed to initialize Twitch client: %s", e)
            return False

    def _run_async(self, coro: Any) -> Any:
        """Run async coroutine in dedicated event loop."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop.run_until_complete(coro)

    async def _async_connect(self) -> bool:
        """Async connect and authenticate with Twitch."""
        try:
            # Create Twitch instance
            self._twitch = await Twitch(self._client_id, self._client_secret)

            # Check for saved tokens
            tokens = self._load_tokens()
            if tokens:
                try:
                    await self._twitch.set_user_authentication(
                        tokens["access_token"],
                        [AuthScope(s) for s in TWITCH_SCOPES],
                        tokens.get("refresh_token"),
                    )
                    # Test if tokens still valid
                    users = await self._twitch.get_users()
                    if users and users.data:
                        self._user_id = users.data[0].id
                        self._broadcaster_id = self._user_id
                        self._connected = True
                        self._initialized = True
                        logger.info(
                            "Twitch connected (cached tokens) as: %s",
                            users.data[0].display_name
                        )
                        return True
                except Exception as e:
                    logger.debug("Cached tokens invalid, re-authenticating: %s", e)

            # OAuth flow - opens browser
            auth = UserAuthenticator(
                self._twitch,
                [AuthScope(s) for s in TWITCH_SCOPES],
                force_verify=False,
            )
            token, refresh = await auth.authenticate()
            await self._twitch.set_user_authentication(
                token,
                [AuthScope(s) for s in TWITCH_SCOPES],
                refresh,
            )

            # Save tokens
            self._save_tokens(token, refresh)

            # Get user ID
            users = await self._twitch.get_users()
            if not users or not users.data:
                logger.error("Failed to get Twitch user info")
                return False

            self._user_id = users.data[0].id
            self._broadcaster_id = self._user_id
            self._connected = True
            self._initialized = True

            logger.info(
                "Twitch connected as: %s (ID: %s)",
                users.data[0].display_name,
                self._user_id
            )
            return True

        except Exception as e:
            logger.error("Twitch connection failed: %s", e)
            self._connected = False
            return False

    def _load_tokens(self) -> dict | None:
        """Load tokens from disk."""
        if not TOKEN_FILE.exists():
            return None
        try:
            with open(TOKEN_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.debug("Failed to load Twitch tokens: %s", e)
            return None

    def _save_tokens(self, access_token: str, refresh_token: str | None) -> None:
        """Save tokens to disk."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }, f)
            logger.debug("Twitch tokens saved")
        except Exception as e:
            logger.warning("Failed to save Twitch tokens: %s", e)

    def _rate_limit(self) -> bool:
        """Check and enforce rate limiting.

        Returns:
            True if action is allowed, False if rate limited.
        """
        now = time.time()
        if now - self._last_action_time < MIN_ACTION_INTERVAL:
            logger.debug("Twitch action rate limited")
            return False
        self._last_action_time = now
        return True

    def _run_action(self, coro: Any) -> Any:
        """Run an async action with rate limiting."""
        if not self._connected:
            logger.warning("Twitch not connected")
            return None

        if not self._rate_limit():
            return None

        try:
            future = self._executor.submit(self._run_async, coro)
            return future.result(timeout=10)
        except Exception as e:
            logger.warning("Twitch action failed: %s", e)
            return None

    # ========== Stream Actions ==========

    def create_marker(self, description: str = "") -> bool:
        """Create a stream marker.

        Args:
            description: Optional marker description (max 140 chars).

        Returns:
            True if marker created successfully.
        """
        async def _create():
            if description:
                desc = description[:140]
            else:
                desc = None
            await self._twitch.create_stream_marker(
                user_id=self._broadcaster_id,
                description=desc
            )
            logger.info("Twitch marker created: %s", description or "(no description)")
            return True

        result = self._run_action(_create())
        return result is True

    def create_clip(self) -> str | None:
        """Create a clip of the current stream.

        Returns:
            Clip URL if successful, None otherwise.
        """
        async def _create():
            result = await self._twitch.create_clip(
                broadcaster_id=self._broadcaster_id,
                has_delay=False
            )
            if result and result.data:
                clip_id = result.data[0].id
                edit_url = result.data[0].edit_url
                logger.info("Twitch clip created: %s", clip_id)
                return edit_url
            return None

        return self._run_action(_create())

    def send_chat(self, message: str) -> bool:
        """Send a chat message to your channel.

        Args:
            message: Message to send (max 500 chars).

        Returns:
            True if message sent successfully.
        """
        async def _send():
            msg = message[:500]
            await self._twitch.send_chat_message(
                broadcaster_id=self._broadcaster_id,
                sender_id=self._user_id,
                message=msg
            )
            logger.info("Twitch chat sent: %s", msg[:50])
            return True

        result = self._run_action(_send())
        return result is True

    def update_title(self, title: str) -> bool:
        """Update stream title.

        Args:
            title: New stream title.

        Returns:
            True if title updated successfully.
        """
        async def _update():
            await self._twitch.modify_channel_information(
                broadcaster_id=self._broadcaster_id,
                title=title
            )
            logger.info("Twitch title updated: %s", title)
            return True

        result = self._run_action(_update())
        return result is True

    def update_game(self, game_name: str) -> bool:
        """Update stream game/category.

        Args:
            game_name: Game/category name.

        Returns:
            True if game updated successfully.
        """
        async def _update():
            # First search for the game to get its ID
            games = await self._twitch.get_games(names=[game_name])
            if not games or not games.data:
                logger.warning("Game not found: %s", game_name)
                return False

            game_id = games.data[0].id
            await self._twitch.modify_channel_information(
                broadcaster_id=self._broadcaster_id,
                game_id=game_id
            )
            logger.info("Twitch game updated: %s", game_name)
            return True

        result = self._run_action(_update())
        return result is True

    def get_stream_info(self) -> dict[str, Any] | None:
        """Get current stream information.

        Returns:
            Dict with stream info or None if not streaming.
        """
        async def _get():
            streams = await self._twitch.get_streams(user_id=[self._broadcaster_id])
            if not streams or not streams.data:
                return None

            stream = streams.data[0]
            return {
                "title": stream.title,
                "game_name": stream.game_name,
                "viewer_count": stream.viewer_count,
                "started_at": stream.started_at.isoformat() if stream.started_at else None,
                "is_live": True,
            }

        return self._run_action(_get())

    def is_live(self) -> bool:
        """Check if currently streaming.

        Returns:
            True if live, False otherwise.
        """
        info = self.get_stream_info()
        return info is not None and info.get("is_live", False)

    def disconnect(self) -> None:
        """Disconnect from Twitch API."""
        if self._twitch:
            try:
                self._run_async(self._twitch.close())
            except Exception:
                pass
        self._twitch = None
        self._connected = False
        self._initialized = False
        logger.info("Twitch disconnected")


# Global instance
twitch = TwitchClient()


def get_twitch_client() -> TwitchClient:
    """Get the Twitch client singleton.

    Returns:
        The TwitchClient instance.
    """
    return TwitchClient()
