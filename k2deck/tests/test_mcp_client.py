"""Tests for k2deck.mcp.client — K2 Deck API HTTP client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from k2deck.mcp import client as client_module
from k2deck.mcp.client import K2DeckClient, get_client


class TestK2DeckClient:
    def setup_method(self):
        """Reset singleton before each test."""
        client_module._client = None

    def teardown_method(self):
        """Reset singleton after each test."""
        client_module._client = None

    @pytest.mark.asyncio
    async def test_get_success(self):
        """GET returns parsed JSON on success."""
        c = K2DeckClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"connected": True}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_resp
            mock_get.return_value = mock_http

            result = await c.get("/api/k2/state")
            assert result == {"connected": True}
            mock_http.get.assert_called_once_with("/api/k2/state")

    @pytest.mark.asyncio
    async def test_put_success(self):
        """PUT sends JSON body and returns response."""
        c = K2DeckClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "ok"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.put.return_value = mock_resp
            mock_get.return_value = mock_http

            result = await c.put("/api/k2/state/layer", json={"layer": 2})
            assert result == {"message": "ok"}
            mock_http.put.assert_called_once_with(
                "/api/k2/state/layer", json={"layer": 2}
            )

    @pytest.mark.asyncio
    async def test_post_success(self):
        """POST sends JSON body and returns response."""
        c = K2DeckClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": "triggered"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_get.return_value = mock_http

            result = await c.post("/api/k2/trigger", json={"action": "hotkey"})
            assert result == {"message": "triggered"}

    @pytest.mark.asyncio
    async def test_is_alive_true(self):
        """is_alive returns True when server responds 200."""
        c = K2DeckClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_resp
            mock_get.return_value = mock_http

            assert await c.is_alive() is True

    @pytest.mark.asyncio
    async def test_is_alive_false_on_connect_error(self):
        """is_alive returns False when server is unreachable."""
        c = K2DeckClient()

        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get.side_effect = httpx.ConnectError("refused")
            mock_get.return_value = mock_http

            assert await c.is_alive() is False

    @pytest.mark.asyncio
    async def test_close(self):
        """close() calls aclose on underlying client."""
        c = K2DeckClient()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        c._client = mock_http

        await c.close()
        mock_http.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_already_closed(self):
        """close() is no-op if client already closed."""
        c = K2DeckClient()
        mock_http = AsyncMock()
        mock_http.is_closed = True
        c._client = mock_http

        await c.close()
        mock_http.aclose.assert_not_called()

    def test_get_client_singleton(self):
        """get_client returns the same instance."""
        a = get_client()
        b = get_client()
        assert a is b

    def test_get_client_creates_new_after_reset(self):
        """get_client creates new instance after singleton reset."""
        a = get_client()
        client_module._client = None
        b = get_client()
        assert a is not b
