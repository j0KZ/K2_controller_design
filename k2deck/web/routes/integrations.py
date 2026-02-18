"""Integrations API Routes - OBS, Spotify, Twitch status and control.

Endpoints:
- GET  /api/integrations                    - Status of all integrations
- GET  /api/integrations/{name}/status      - Status of specific integration
- POST /api/integrations/{name}/connect     - Connect/authenticate
- POST /api/integrations/{name}/disconnect  - Disconnect
"""

import logging
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class IntegrationName(str, Enum):
    """Available integrations."""

    OBS = "obs"
    SPOTIFY = "spotify"
    TWITCH = "twitch"


class IntegrationStatus(BaseModel):
    """Status of an integration."""

    name: str
    available: bool  # Library installed
    connected: bool
    status: str  # "connected", "disconnected", "error", "unavailable"
    error: str | None = None
    details: dict[str, Any] | None = None


class AllIntegrationsStatus(BaseModel):
    """Status of all integrations."""

    obs: IntegrationStatus
    spotify: IntegrationStatus
    twitch: IntegrationStatus


class ConnectRequest(BaseModel):
    """Request body for connection."""

    host: str | None = None
    port: int | None = None
    password: str | None = None
    # Spotify-specific
    client_id: str | None = None
    client_secret: str | None = None
    redirect_uri: str | None = None


def _get_obs_status() -> IntegrationStatus:
    """Get OBS integration status.

    Returns:
        OBS status.
    """
    try:
        from k2deck.core.obs_client import get_obs_client

        client = get_obs_client()

        if not client.is_available:
            return IntegrationStatus(
                name="obs",
                available=False,
                connected=False,
                status="unavailable",
                error="obsws-python not installed. Run: pip install obsws-python",
            )

        if client.is_connected:
            return IntegrationStatus(
                name="obs",
                available=True,
                connected=True,
                status="connected",
                details={"scenes": client.get_scenes()},
            )
        else:
            return IntegrationStatus(
                name="obs",
                available=True,
                connected=False,
                status="disconnected",
                error=client.last_error,
            )

    except Exception as e:
        return IntegrationStatus(
            name="obs",
            available=False,
            connected=False,
            status="error",
            error=str(e),
        )


def _get_spotify_status() -> IntegrationStatus:
    """Get Spotify integration status.

    Returns:
        Spotify status.
    """
    try:
        from k2deck.core.spotify_client import get_spotify_client

        client = get_spotify_client()

        if not client.is_available:
            return IntegrationStatus(
                name="spotify",
                available=False,
                connected=False,
                status="unavailable",
                error="spotipy not installed. Run: pip install spotipy",
            )

        if client.is_authenticated:
            return IntegrationStatus(
                name="spotify",
                available=True,
                connected=True,
                status="connected",
                details={"user": client.get_current_user()},
            )
        else:
            return IntegrationStatus(
                name="spotify",
                available=True,
                connected=False,
                status="disconnected",
            )

    except ImportError:
        return IntegrationStatus(
            name="spotify",
            available=False,
            connected=False,
            status="unavailable",
            error="Spotify client not implemented",
        )
    except Exception as e:
        return IntegrationStatus(
            name="spotify",
            available=False,
            connected=False,
            status="error",
            error=str(e),
        )


def _get_twitch_status() -> IntegrationStatus:
    """Get Twitch integration status.

    Returns:
        Twitch status.
    """
    try:
        from k2deck.core.twitch_client import get_twitch_client

        client = get_twitch_client()

        if not client.is_available:
            return IntegrationStatus(
                name="twitch",
                available=False,
                connected=False,
                status="unavailable",
                error="twitchAPI not installed. Run: pip install twitchAPI",
            )

        if client.is_connected:
            return IntegrationStatus(
                name="twitch",
                available=True,
                connected=True,
                status="connected",
            )
        else:
            return IntegrationStatus(
                name="twitch",
                available=True,
                connected=False,
                status="disconnected",
            )

    except Exception as e:
        return IntegrationStatus(
            name="twitch",
            available=False,
            connected=False,
            status="error",
            error=str(e),
        )


@router.get("")
async def get_all_integrations() -> AllIntegrationsStatus:
    """Get status of all integrations.

    Returns:
        Status for OBS, Spotify, and Twitch.
    """
    return AllIntegrationsStatus(
        obs=_get_obs_status(),
        spotify=_get_spotify_status(),
        twitch=_get_twitch_status(),
    )


@router.get("/{name}/status")
async def get_integration_status(name: IntegrationName) -> IntegrationStatus:
    """Get status of a specific integration.

    Args:
        name: Integration name (obs, spotify, twitch).

    Returns:
        Integration status.
    """
    if name == IntegrationName.OBS:
        return _get_obs_status()
    elif name == IntegrationName.SPOTIFY:
        return _get_spotify_status()
    elif name == IntegrationName.TWITCH:
        return _get_twitch_status()
    else:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {name}")


@router.post("/{name}/connect")
async def connect_integration(
    name: IntegrationName, body: ConnectRequest | None = None
) -> IntegrationStatus:
    """Connect to an integration.

    Args:
        name: Integration name.
        body: Connection parameters.

    Returns:
        Updated integration status.
    """
    if name == IntegrationName.OBS:
        try:
            from k2deck.core.obs_client import get_obs_client

            client = get_obs_client()

            if not client.is_available:
                raise HTTPException(
                    status_code=400,
                    detail="obsws-python not installed. Run: pip install obsws-python",
                )

            # Configure if parameters provided
            if body:
                client.configure(
                    host=body.host or "localhost",
                    port=body.port or 4455,
                    password=body.password or "",
                )

            # Attempt connection
            if client.connect():
                from k2deck.web.websocket.manager import broadcast_integration_change

                broadcast_integration_change("obs", "connected")
                return _get_obs_status()
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to connect to OBS: {client.last_error}",
                )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OBS connection error: {e}")

    elif name == IntegrationName.SPOTIFY:
        # Spotify requires OAuth flow
        raise HTTPException(
            status_code=501,
            detail="Spotify OAuth flow not implemented. Configure via config file.",
        )

    elif name == IntegrationName.TWITCH:
        # Twitch requires OAuth flow
        raise HTTPException(
            status_code=501,
            detail="Twitch OAuth flow not implemented. Configure via config file.",
        )

    else:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {name}")


@router.post("/{name}/disconnect")
async def disconnect_integration(name: IntegrationName) -> IntegrationStatus:
    """Disconnect from an integration.

    Args:
        name: Integration name.

    Returns:
        Updated integration status.
    """
    if name == IntegrationName.OBS:
        try:
            from k2deck.core.obs_client import get_obs_client

            client = get_obs_client()
            client.disconnect()

            from k2deck.web.websocket.manager import broadcast_integration_change

            broadcast_integration_change("obs", "disconnected")

            return _get_obs_status()

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to disconnect: {e}")

    elif name == IntegrationName.SPOTIFY:
        # TODO: Implement Spotify disconnect
        raise HTTPException(
            status_code=501, detail="Spotify disconnect not implemented"
        )

    elif name == IntegrationName.TWITCH:
        # TODO: Implement Twitch disconnect
        raise HTTPException(status_code=501, detail="Twitch disconnect not implemented")

    else:
        raise HTTPException(status_code=404, detail=f"Unknown integration: {name}")
