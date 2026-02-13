"""HTTP Client for K2 Deck REST API.

Handles all HTTP communication between the MCP server and K2 Deck's
FastAPI backend running on localhost:8420.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


class K2DeckAPIError(Exception):
    """Raised when K2 Deck API request fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"K2 Deck API Error {status_code}: {message}")


class K2DeckClient:
    """Async HTTP client for the K2 Deck REST API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8420") -> None:
        self._base = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self._base, timeout=10.0)
        return self._client

    async def get(self, path: str) -> dict:
        """GET request to K2 Deck API."""
        client = await self._get_client()
        resp = await client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, json: dict) -> dict:
        """PUT request to K2 Deck API."""
        client = await self._get_client()
        resp = await client.put(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json: dict | None = None) -> dict:
        """POST request to K2 Deck API."""
        client = await self._get_client()
        resp = await client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def is_alive(self) -> bool:
        """Check if K2 Deck web server is responding."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/k2/state")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
_client: K2DeckClient | None = None


def get_client() -> K2DeckClient:
    """Get the K2 Deck API client singleton."""
    global _client
    if _client is None:
        _client = K2DeckClient()
    return _client
