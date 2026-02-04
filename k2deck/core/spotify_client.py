"""Spotify API client wrapper using spotipy."""

import logging
import os
from pathlib import Path
from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)

# Load .env file if it exists
_ENV_FILE = Path(__file__).parent.parent / "config" / ".env"
if _ENV_FILE.exists():
    try:
        with open(_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
        logger.debug("Loaded Spotify credentials from .env")
    except Exception as e:
        logger.warning("Failed to load .env: %s", e)

# Default paths
CONFIG_DIR = Path(__file__).parent.parent / "config"
TOKEN_CACHE_PATH = CONFIG_DIR / "spotify_token.json"

# Required scopes for K2 Deck functionality
SPOTIFY_SCOPES = [
    "user-read-playback-state",      # Get current playback
    "user-modify-playback-state",    # Play, pause, seek, volume, etc.
    "user-read-currently-playing",   # Get current track
    "user-library-read",             # Check if track is liked
    "user-library-modify",           # Like/unlike tracks
    "playlist-read-private",         # Read playlists
    "playlist-read-collaborative",   # Read collaborative playlists
]


class SpotifyClient:
    """Singleton wrapper for Spotify API client."""

    _instance: "SpotifyClient | None" = None
    _sp: spotipy.Spotify | None = None
    _initialized: bool = False

    def __new__(cls) -> "SpotifyClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str = "http://127.0.0.1:8080/api/auth/spotify/callback",
    ) -> bool:
        """Initialize the Spotify client with OAuth.

        Args:
            client_id: Spotify app client ID (or set SPOTIPY_CLIENT_ID env var)
            client_secret: Spotify app client secret (or set SPOTIPY_CLIENT_SECRET env var)
            redirect_uri: OAuth redirect URI (default: http://localhost:8888/callback)

        Returns:
            True if initialization successful.
        """
        if self._initialized and self._sp:
            return True

        # Use env vars if not provided
        client_id = client_id or os.environ.get("SPOTIPY_CLIENT_ID")
        client_secret = client_secret or os.environ.get("SPOTIPY_CLIENT_SECRET")

        if not client_id or not client_secret:
            logger.warning(
                "Spotify credentials not configured. "
                "Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables, "
                "or create k2deck/config/.env with these values."
            )
            return False

        try:
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=" ".join(SPOTIFY_SCOPES),
                cache_path=str(TOKEN_CACHE_PATH),
                open_browser=True,
            )

            self._sp = spotipy.Spotify(auth_manager=auth_manager)

            # Test connection
            user = self._sp.current_user()
            logger.info("Spotify connected as: %s", user.get("display_name", "Unknown"))
            self._initialized = True
            return True

        except Exception as e:
            logger.error("Failed to initialize Spotify client: %s", e)
            self._initialized = False
            return False

    @property
    def is_ready(self) -> bool:
        """Check if client is initialized and ready."""
        return self._initialized and self._sp is not None

    @property
    def client(self) -> spotipy.Spotify | None:
        """Get the raw spotipy client."""
        return self._sp

    # ========== Playback Control ==========

    def play(self) -> bool:
        """Start or resume playback."""
        if not self.is_ready:
            return False
        try:
            self._sp.start_playback()
            logger.debug("Spotify: play")
            return True
        except Exception as e:
            logger.warning("Spotify play failed: %s", e)
            return False

    def pause(self) -> bool:
        """Pause playback."""
        if not self.is_ready:
            return False
        try:
            self._sp.pause_playback()
            logger.debug("Spotify: pause")
            return True
        except Exception as e:
            logger.warning("Spotify pause failed: %s", e)
            return False

    def play_pause(self) -> bool:
        """Toggle play/pause based on current state."""
        if not self.is_ready:
            return False
        try:
            playback = self._sp.current_playback()
            if playback and playback.get("is_playing"):
                return self.pause()
            else:
                return self.play()
        except Exception as e:
            logger.warning("Spotify play/pause failed: %s", e)
            return False

    def next_track(self) -> bool:
        """Skip to next track."""
        if not self.is_ready:
            return False
        try:
            self._sp.next_track()
            logger.debug("Spotify: next track")
            return True
        except Exception as e:
            logger.warning("Spotify next failed: %s", e)
            return False

    def previous_track(self) -> bool:
        """Go to previous track."""
        if not self.is_ready:
            return False
        try:
            self._sp.previous_track()
            logger.debug("Spotify: previous track")
            return True
        except Exception as e:
            logger.warning("Spotify previous failed: %s", e)
            return False

    def seek(self, position_ms: int) -> bool:
        """Seek to position in current track.

        Args:
            position_ms: Position in milliseconds.
        """
        if not self.is_ready:
            return False
        try:
            self._sp.seek_track(position_ms)
            logger.debug("Spotify: seek to %d ms", position_ms)
            return True
        except Exception as e:
            logger.warning("Spotify seek failed: %s", e)
            return False

    def seek_relative(self, delta_ms: int) -> bool:
        """Seek relative to current position.

        Args:
            delta_ms: Milliseconds to seek (positive = forward, negative = backward).
        """
        if not self.is_ready:
            return False
        try:
            playback = self._sp.current_playback()
            if not playback:
                return False

            current_pos = playback.get("progress_ms", 0)
            duration = playback.get("item", {}).get("duration_ms", 0)
            new_pos = max(0, min(current_pos + delta_ms, duration))

            return self.seek(new_pos)
        except Exception as e:
            logger.warning("Spotify seek relative failed: %s", e)
            return False

    # ========== Volume Control ==========

    def set_volume(self, volume_percent: int) -> bool:
        """Set playback volume.

        Args:
            volume_percent: Volume 0-100.
        """
        if not self.is_ready:
            return False
        try:
            volume_percent = max(0, min(100, volume_percent))
            self._sp.volume(volume_percent)
            logger.debug("Spotify: volume %d%%", volume_percent)
            return True
        except Exception as e:
            logger.warning("Spotify volume failed: %s", e)
            return False

    def get_volume(self) -> int | None:
        """Get current volume."""
        if not self.is_ready:
            return None
        try:
            playback = self._sp.current_playback()
            if playback and playback.get("device"):
                return playback["device"].get("volume_percent")
            return None
        except Exception as e:
            logger.warning("Spotify get volume failed: %s", e)
            return None

    # ========== Library (Like/Unlike) ==========

    def is_track_saved(self, track_id: str | None = None) -> bool | None:
        """Check if current track is saved to library.

        Args:
            track_id: Track ID (or None for current track).
        """
        if not self.is_ready:
            return None
        try:
            if not track_id:
                current = self._sp.current_playback()
                if not current or not current.get("item"):
                    return None
                track_id = current["item"]["id"]

            result = self._sp.current_user_saved_tracks_contains([track_id])
            return result[0] if result else None
        except Exception as e:
            logger.warning("Spotify check saved failed: %s", e)
            return None

    def save_track(self, track_id: str | None = None) -> bool:
        """Save track to library (Like).

        Args:
            track_id: Track ID (or None for current track).
        """
        if not self.is_ready:
            return False
        try:
            if not track_id:
                current = self._sp.current_playback()
                if not current or not current.get("item"):
                    return False
                track_id = current["item"]["id"]

            self._sp.current_user_saved_tracks_add([track_id])
            logger.info("Spotify: saved track to library")
            return True
        except Exception as e:
            logger.warning("Spotify save track failed: %s", e)
            return False

    def remove_track(self, track_id: str | None = None) -> bool:
        """Remove track from library (Unlike).

        Args:
            track_id: Track ID (or None for current track).
        """
        if not self.is_ready:
            return False
        try:
            if not track_id:
                current = self._sp.current_playback()
                if not current or not current.get("item"):
                    return False
                track_id = current["item"]["id"]

            self._sp.current_user_saved_tracks_delete([track_id])
            logger.info("Spotify: removed track from library")
            return True
        except Exception as e:
            logger.warning("Spotify remove track failed: %s", e)
            return False

    def toggle_like(self) -> bool | None:
        """Toggle like status of current track.

        Returns:
            True if now liked, False if now unliked, None on error.
        """
        if not self.is_ready:
            return None
        try:
            is_saved = self.is_track_saved()
            if is_saved is None:
                return None

            if is_saved:
                self.remove_track()
                return False
            else:
                self.save_track()
                return True
        except Exception as e:
            logger.warning("Spotify toggle like failed: %s", e)
            return None

    # ========== Shuffle/Repeat ==========

    def set_shuffle(self, state: bool) -> bool:
        """Set shuffle mode."""
        if not self.is_ready:
            return False
        try:
            self._sp.shuffle(state)
            logger.debug("Spotify: shuffle %s", "on" if state else "off")
            return True
        except Exception as e:
            logger.warning("Spotify shuffle failed: %s", e)
            return False

    def toggle_shuffle(self) -> bool | None:
        """Toggle shuffle mode.

        Returns:
            New shuffle state, or None on error.
        """
        if not self.is_ready:
            return None
        try:
            playback = self._sp.current_playback()
            if not playback:
                return None

            current_shuffle = playback.get("shuffle_state", False)
            new_state = not current_shuffle
            self._sp.shuffle(new_state)
            logger.info("Spotify: shuffle %s", "on" if new_state else "off")
            return new_state
        except Exception as e:
            logger.warning("Spotify toggle shuffle failed: %s", e)
            return None

    def set_repeat(self, state: str) -> bool:
        """Set repeat mode.

        Args:
            state: "track", "context", or "off".
        """
        if not self.is_ready:
            return False
        try:
            self._sp.repeat(state)
            logger.debug("Spotify: repeat %s", state)
            return True
        except Exception as e:
            logger.warning("Spotify repeat failed: %s", e)
            return False

    def cycle_repeat(self) -> str | None:
        """Cycle through repeat modes: off -> context -> track -> off.

        Returns:
            New repeat state, or None on error.
        """
        if not self.is_ready:
            return None
        try:
            playback = self._sp.current_playback()
            if not playback:
                return None

            current = playback.get("repeat_state", "off")
            cycle = {"off": "context", "context": "track", "track": "off"}
            new_state = cycle.get(current, "off")
            self._sp.repeat(new_state)
            logger.info("Spotify: repeat %s", new_state)
            return new_state
        except Exception as e:
            logger.warning("Spotify cycle repeat failed: %s", e)
            return None

    # ========== State Info ==========

    def get_current_track(self) -> dict[str, Any] | None:
        """Get info about currently playing track."""
        if not self.is_ready:
            return None
        try:
            playback = self._sp.current_playback()
            if not playback or not playback.get("item"):
                return None

            item = playback["item"]
            return {
                "id": item.get("id"),
                "name": item.get("name"),
                "artist": ", ".join(a["name"] for a in item.get("artists", [])),
                "album": item.get("album", {}).get("name"),
                "duration_ms": item.get("duration_ms"),
                "progress_ms": playback.get("progress_ms"),
                "is_playing": playback.get("is_playing"),
                "shuffle": playback.get("shuffle_state"),
                "repeat": playback.get("repeat_state"),
                "volume": playback.get("device", {}).get("volume_percent"),
            }
        except Exception as e:
            logger.warning("Spotify get current track failed: %s", e)
            return None

    def is_playing(self) -> bool | None:
        """Check if Spotify is currently playing."""
        if not self.is_ready:
            return None
        try:
            playback = self._sp.current_playback()
            return playback.get("is_playing") if playback else False
        except Exception as e:
            logger.warning("Spotify is_playing check failed: %s", e)
            return None


# Global instance
spotify = SpotifyClient()
