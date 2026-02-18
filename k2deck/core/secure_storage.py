"""Secure storage for credentials and tokens.

Uses Windows DPAPI for token encryption and keyring for API secrets.
Falls back to plain storage if secure methods unavailable.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check for keyring availability
try:
    import keyring

    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False
    keyring = None

# Check for DPAPI availability (Windows only)
try:
    import win32crypt

    HAS_DPAPI = True
except ImportError:
    HAS_DPAPI = False
    win32crypt = None

# Service name for keyring
KEYRING_SERVICE = "k2deck"


# =============================================================================
# Keyring-based credential storage (for API secrets)
# =============================================================================


def store_credential(name: str, value: str) -> bool:
    """Store a credential securely using OS keyring.

    Args:
        name: Credential name (e.g., "spotify_client_id")
        value: Credential value

    Returns:
        True if stored successfully.
    """
    if not HAS_KEYRING:
        logger.warning("keyring not available, credential not stored securely")
        return False

    try:
        keyring.set_password(KEYRING_SERVICE, name, value)
        logger.debug("Stored credential: %s", name)
        return True
    except Exception as e:
        logger.error("Failed to store credential %s: %s", name, e)
        return False


def get_credential(name: str) -> str | None:
    """Retrieve a credential from OS keyring.

    Args:
        name: Credential name

    Returns:
        Credential value or None if not found.
    """
    if not HAS_KEYRING:
        return None

    try:
        value = keyring.get_password(KEYRING_SERVICE, name)
        return value
    except Exception as e:
        logger.debug("Failed to get credential %s: %s", name, e)
        return None


def delete_credential(name: str) -> bool:
    """Delete a credential from OS keyring.

    Args:
        name: Credential name

    Returns:
        True if deleted successfully.
    """
    if not HAS_KEYRING:
        return False

    try:
        keyring.delete_password(KEYRING_SERVICE, name)
        logger.debug("Deleted credential: %s", name)
        return True
    except Exception as e:
        logger.debug("Failed to delete credential %s: %s", name, e)
        return False


def has_keyring() -> bool:
    """Check if keyring is available."""
    return HAS_KEYRING


# =============================================================================
# DPAPI-based token encryption (for OAuth tokens)
# =============================================================================


def encrypt_data(data: bytes) -> bytes | None:
    """Encrypt data using Windows DPAPI.

    Args:
        data: Data to encrypt

    Returns:
        Encrypted data or None if encryption failed.
    """
    if not HAS_DPAPI:
        logger.debug("DPAPI not available, returning unencrypted data")
        return data

    try:
        encrypted = win32crypt.CryptProtectData(
            data,
            "K2Deck Token",  # Description
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            0,  # Flags
        )
        return encrypted
    except Exception as e:
        logger.error("DPAPI encryption failed: %s", e)
        return None


def decrypt_data(data: bytes) -> bytes | None:
    """Decrypt data using Windows DPAPI.

    Args:
        data: Encrypted data

    Returns:
        Decrypted data or None if decryption failed.
    """
    if not HAS_DPAPI:
        logger.debug("DPAPI not available, returning data as-is")
        return data

    try:
        _, decrypted = win32crypt.CryptUnprotectData(
            data,
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            0,  # Flags
        )
        return decrypted
    except Exception as e:
        logger.error("DPAPI decryption failed: %s", e)
        return None


def save_encrypted_json(path: Path, data: dict[str, Any]) -> bool:
    """Save JSON data encrypted with DPAPI.

    Args:
        path: File path
        data: Data to save

    Returns:
        True if saved successfully.
    """
    try:
        json_bytes = json.dumps(data).encode("utf-8")

        if HAS_DPAPI:
            encrypted = encrypt_data(json_bytes)
            if encrypted is None:
                return False
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encrypted)
            logger.debug("Saved encrypted data to %s", path)
        else:
            # Fallback: save as plain JSON with warning
            logger.warning("DPAPI unavailable, saving tokens in plain text")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")

        return True
    except Exception as e:
        logger.error("Failed to save encrypted data: %s", e)
        return False


def load_encrypted_json(path: Path) -> dict[str, Any] | None:
    """Load JSON data encrypted with DPAPI.

    Args:
        path: File path

    Returns:
        Loaded data or None if failed.
    """
    if not path.exists():
        return None

    try:
        raw_data = path.read_bytes()

        if HAS_DPAPI:
            decrypted = decrypt_data(raw_data)
            if decrypted is None:
                # Try reading as plain JSON (migration from old format)
                try:
                    return json.loads(raw_data.decode("utf-8"))
                except Exception:
                    return None
            return json.loads(decrypted.decode("utf-8"))
        else:
            # Fallback: read as plain JSON
            return json.loads(raw_data.decode("utf-8"))
    except Exception as e:
        logger.error("Failed to load encrypted data: %s", e)
        return None


def has_dpapi() -> bool:
    """Check if DPAPI is available."""
    return HAS_DPAPI


# =============================================================================
# High-level helpers for Spotify/Twitch credentials
# =============================================================================


def get_spotify_credentials() -> tuple[str | None, str | None]:
    """Get Spotify client ID and secret from keyring.

    Returns:
        Tuple of (client_id, client_secret) or (None, None) if not found.
    """
    client_id = get_credential("spotify_client_id")
    client_secret = get_credential("spotify_client_secret")
    return client_id, client_secret


def set_spotify_credentials(client_id: str, client_secret: str) -> bool:
    """Store Spotify credentials in keyring.

    Args:
        client_id: Spotify app client ID
        client_secret: Spotify app client secret

    Returns:
        True if both stored successfully.
    """
    id_ok = store_credential("spotify_client_id", client_id)
    secret_ok = store_credential("spotify_client_secret", client_secret)
    return id_ok and secret_ok


def get_twitch_credentials() -> tuple[str | None, str | None]:
    """Get Twitch client ID and secret from keyring.

    Returns:
        Tuple of (client_id, client_secret) or (None, None) if not found.
    """
    client_id = get_credential("twitch_client_id")
    client_secret = get_credential("twitch_client_secret")
    return client_id, client_secret


def set_twitch_credentials(client_id: str, client_secret: str) -> bool:
    """Store Twitch credentials in keyring.

    Args:
        client_id: Twitch app client ID
        client_secret: Twitch app client secret

    Returns:
        True if both stored successfully.
    """
    id_ok = store_credential("twitch_client_id", client_id)
    secret_ok = store_credential("twitch_client_secret", client_secret)
    return id_ok and secret_ok
