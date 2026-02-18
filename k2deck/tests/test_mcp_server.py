"""Tests for k2deck.mcp.server — MCP tool handlers."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from k2deck.mcp import client as client_module


class TestMCPToolList:
    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self):
        """list_tools returns all 10 MCP tools."""
        from k2deck.mcp.server import list_tools

        tools = await list_tools()
        names = [t.name for t in tools]
        assert len(tools) == 10
        assert "get_k2_state" in names
        assert "get_k2_layout" in names
        assert "set_led" in names
        assert "set_layer" in names
        assert "list_profiles" in names
        assert "get_profile" in names
        assert "activate_profile" in names
        assert "get_integrations" in names
        assert "trigger_action" in names
        assert "get_timers" in names

    @pytest.mark.asyncio
    async def test_set_led_schema_has_note_required(self):
        """set_led tool requires 'note' parameter."""
        from k2deck.mcp.server import list_tools

        tools = await list_tools()
        led_tool = next(t for t in tools if t.name == "set_led")
        assert "note" in led_tool.inputSchema["required"]
        assert "red" in led_tool.inputSchema["properties"]["color"]["enum"]


class TestMCPCallTool:
    def setup_method(self):
        """Reset client singleton."""
        client_module._client = None

    def teardown_method(self):
        """Reset client singleton."""
        client_module._client = None

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_get_k2_state(self, mock_get_client):
        """get_k2_state returns JSON state."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "connected": False,
            "layer": 1,
            "leds": {},
            "analog": {},
        }
        mock_get_client.return_value = mock_client

        result = await call_tool("get_k2_state", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["layer"] == 1
        mock_client.get.assert_called_once_with("/api/k2/state")

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_get_k2_layout(self, mock_get_client):
        """get_k2_layout returns hardware layout."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {"rows": [], "totalControls": 52}
        mock_get_client.return_value = mock_client

        result = await call_tool("get_k2_layout", {})
        data = json.loads(result[0].text)
        assert data["totalControls"] == 52
        mock_client.get.assert_called_once_with("/api/k2/layout")

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_set_led_on(self, mock_get_client):
        """set_led sends PUT with correct note in path."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.put.return_value = {"message": "LED 36 set to green"}
        mock_get_client.return_value = mock_client

        result = await call_tool("set_led", {"note": 36, "color": "green", "on": True})
        assert "LED 36 set to green" in result[0].text
        mock_client.put.assert_called_once_with(
            "/api/k2/state/leds/36",
            json={"note": 36, "color": "green", "on": True},
        )

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_set_led_off(self, mock_get_client):
        """set_led with on=false sends null color."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.put.return_value = {"message": "LED 36 set to off"}
        mock_get_client.return_value = mock_client

        await call_tool("set_led", {"note": 36, "on": False})
        mock_client.put.assert_called_once_with(
            "/api/k2/state/leds/36",
            json={"note": 36, "color": None, "on": False},
        )

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_set_layer(self, mock_get_client):
        """set_layer sends PUT with layer number."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.put.return_value = {"layer": 2, "previous": 1}
        mock_get_client.return_value = mock_client

        result = await call_tool("set_layer", {"layer": 2})
        assert "Layer set to 2" in result[0].text
        assert "was 1" in result[0].text

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_list_profiles(self, mock_get_client):
        """list_profiles returns profile list."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "profiles": [{"name": "default", "active": True}],
            "active": "default",
        }
        mock_get_client.return_value = mock_client

        result = await call_tool("list_profiles", {})
        data = json.loads(result[0].text)
        assert data["active"] == "default"

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_get_profile(self, mock_get_client):
        """get_profile fetches specific profile."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {"name": "gaming", "mappings": {}}
        mock_get_client.return_value = mock_client

        result = await call_tool("get_profile", {"name": "gaming"})
        data = json.loads(result[0].text)
        assert data["name"] == "gaming"
        mock_client.get.assert_called_once_with("/api/profiles/gaming")

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_activate_profile(self, mock_get_client):
        """activate_profile sends PUT to activate endpoint."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.put.return_value = {"message": "ok", "previous": "default"}
        mock_get_client.return_value = mock_client

        result = await call_tool("activate_profile", {"name": "gaming"})
        assert "gaming" in result[0].text
        assert "default" in result[0].text
        mock_client.put.assert_called_once_with(
            "/api/profiles/gaming/activate", json={}
        )

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_get_integrations(self, mock_get_client):
        """get_integrations returns integration status."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "obs": {"connected": False},
            "spotify": {"connected": True},
            "twitch": {"connected": False},
        }
        mock_get_client.return_value = mock_client

        result = await call_tool("get_integrations", {})
        data = json.loads(result[0].text)
        assert data["spotify"]["connected"] is True

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_trigger_action(self, mock_get_client):
        """trigger_action sends POST with correct body."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.post.return_value = {"message": "Action 'timer_start' triggered"}
        mock_get_client.return_value = mock_client

        result = await call_tool(
            "trigger_action",
            {"action": "timer_start", "config": {"name": "test", "seconds": 60}},
        )
        assert "timer_start" in result[0].text
        mock_client.post.assert_called_once_with(
            "/api/k2/trigger",
            json={
                "action": "timer_start",
                "config": {"name": "test", "seconds": 60},
            },
        )

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_get_timers(self, mock_get_client):
        """get_timers returns timer status."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "pomodoro": {"duration": 1500, "remaining": 800, "running": True}
        }
        mock_get_client.return_value = mock_client

        result = await call_tool("get_timers", {})
        data = json.loads(result[0].text)
        assert "pomodoro" in data
        assert data["pomodoro"]["running"] is True

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_get_timers_empty(self, mock_get_client):
        """get_timers returns friendly message when no timers."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.return_value = {}
        mock_get_client.return_value = mock_client

        result = await call_tool("get_timers", {})
        assert "No active timers" in result[0].text

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_unknown_tool(self, mock_get_client):
        """Unknown tool name returns error message."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        result = await call_tool("nonexistent_tool", {})
        assert "Unknown tool: nonexistent_tool" in result[0].text

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_http_error_handled(self, mock_get_client):
        """HTTP errors are caught and returned as text."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "404", request=AsyncMock(), response=mock_resp
        )
        mock_get_client.return_value = mock_client

        result = await call_tool("get_k2_state", {})
        assert "404" in result[0].text

    @pytest.mark.asyncio
    @patch("k2deck.mcp.server.get_client")
    async def test_connect_error_handled(self, mock_get_client):
        """Connection errors are caught with friendly message."""
        from k2deck.mcp.server import call_tool

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("refused")
        mock_get_client.return_value = mock_client

        result = await call_tool("get_k2_state", {})
        assert "Cannot connect" in result[0].text
