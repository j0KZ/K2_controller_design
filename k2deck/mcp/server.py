"""K2 Deck MCP Server — Claude Desktop integration.

Exposes K2 Deck hardware controls as MCP tools so Claude can read state,
set LEDs, switch profiles, and trigger actions via natural language.

Communicates with K2 Deck's REST API on localhost:8420.
Auto-starts the web server if not already running.

Usage:
    python k2deck/mcp/server.py
    python -m k2deck.mcp
"""

import asyncio
import json
import logging
import os
import subprocess
import sys

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Add project root to sys.path for direct execution from Claude Desktop
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from k2deck.mcp.client import get_client  # noqa: E402

logger = logging.getLogger(__name__)

app = Server("k2deck")


# =============================================================================
# Tool Definitions
# =============================================================================


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available K2 Deck tools."""
    return [
        Tool(
            name="get_k2_state",
            description=(
                "Get complete K2 controller state: connection status, "
                "active layer (1-3), current folder, all LED colors, "
                "and analog control positions (faders/pots 0-127)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_k2_layout",
            description=(
                "Get K2 hardware layout: all controls (encoders, pots, "
                "buttons, faders), their types, MIDI note/CC numbers, "
                "and LED capabilities. Use to understand the physical layout."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="set_led",
            description=(
                "Set LED color on a K2 button. Valid notes: 15 (layer), "
                "32-35 (encoder push E1-E4), 36-51 (buttons A-P), "
                "52-53 (bottom encoders E5-E6). "
                "Colors: red, amber, green. Set on=false to turn off."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "note": {
                        "type": "integer",
                        "description": "LED note: 15 (layer), 32-53 (buttons/encoders)",
                    },
                    "color": {
                        "type": "string",
                        "enum": ["red", "amber", "green"],
                        "description": "LED color",
                    },
                    "on": {
                        "type": "boolean",
                        "default": True,
                        "description": "True to turn on, false to turn off",
                    },
                },
                "required": ["note"],
            },
        ),
        Tool(
            name="set_layer",
            description="Switch the active K2 layer. Layers 1-3 available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "layer": {
                        "type": "integer",
                        "enum": [1, 2, 3],
                        "description": "Layer number (1-3)",
                    },
                },
                "required": ["layer"],
            },
        ),
        Tool(
            name="list_profiles",
            description="List all available configuration profiles and which one is active.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_profile",
            description="Get a specific profile's full configuration (mappings, actions, LED defaults).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Profile name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="activate_profile",
            description="Switch to a different configuration profile. Reloads all button mappings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Profile name to activate",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_integrations",
            description="Get connection status of all integrations: OBS, Spotify, Twitch.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="trigger_action",
            description=(
                "Execute a K2 Deck action by type and config. "
                "Action types include: hotkey, volume, timer_start, timer_stop, "
                "timer_toggle, counter, osc_send, sound_play, tts, system, etc. "
                'Config is action-specific (e.g., {"keys": ["ctrl", "c"]} for hotkey).'
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action type (e.g., 'timer_start', 'hotkey')",
                    },
                    "config": {
                        "type": "object",
                        "description": "Action-specific configuration",
                        "default": {},
                    },
                },
                "required": ["action"],
            },
        ),
        Tool(
            name="get_timers",
            description="Get status of all running timers (name, duration, remaining, running).",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


# =============================================================================
# Tool Handlers
# =============================================================================


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls by delegating to K2 Deck REST API."""
    client = get_client()

    try:
        # --- Read-only tools ---
        if name == "get_k2_state":
            state = await client.get("/api/k2/state")
            return [TextContent(type="text", text=json.dumps(state, indent=2))]

        if name == "get_k2_layout":
            layout = await client.get("/api/k2/layout")
            return [TextContent(type="text", text=json.dumps(layout, indent=2))]

        if name == "list_profiles":
            profiles = await client.get("/api/profiles")
            return [TextContent(type="text", text=json.dumps(profiles, indent=2))]

        if name == "get_profile":
            profile_name = arguments.get("name", "default")
            profile = await client.get(f"/api/profiles/{profile_name}")
            return [TextContent(type="text", text=json.dumps(profile, indent=2))]

        if name == "get_integrations":
            integrations = await client.get("/api/integrations")
            return [TextContent(type="text", text=json.dumps(integrations, indent=2))]

        if name == "get_timers":
            timers = await client.get("/api/k2/timers")
            if not timers:
                return [TextContent(type="text", text="No active timers.")]
            return [TextContent(type="text", text=json.dumps(timers, indent=2))]

        # --- Write tools ---
        if name == "set_led":
            note = arguments["note"]
            color = arguments.get("color", "green")
            on = arguments.get("on", True)
            result = await client.put(
                f"/api/k2/state/leds/{note}",
                json={"note": note, "color": color if on else None, "on": on},
            )
            return [TextContent(type="text", text=result.get("message", "LED updated"))]

        if name == "set_layer":
            layer = arguments["layer"]
            result = await client.put(
                "/api/k2/state/layer",
                json={"layer": layer},
            )
            return [
                TextContent(
                    type="text",
                    text=f"Layer set to {layer} (was {result.get('previous', '?')})",
                )
            ]

        if name == "activate_profile":
            profile_name = arguments["name"]
            result = await client.put(f"/api/profiles/{profile_name}/activate", json={})
            return [
                TextContent(
                    type="text",
                    text=f"Profile '{profile_name}' activated (was '{result.get('previous', '?')}')",
                )
            ]

        if name == "trigger_action":
            action_type = arguments["action"]
            action_config = arguments.get("config", {})
            result = await client.post(
                "/api/k2/trigger",
                json={"action": action_type, "config": action_config},
            )
            return [
                TextContent(type="text", text=result.get("message", "Action triggered"))
            ]

        # Unknown tool
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [
            TextContent(
                type="text",
                text=f"K2 Deck API error {e.response.status_code}: {e.response.text}",
            )
        ]
    except httpx.ConnectError:
        return [
            TextContent(
                type="text",
                text="Cannot connect to K2 Deck web server on localhost:8420. Is it running?",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


# =============================================================================
# Web Server Auto-start
# =============================================================================


async def ensure_web_server() -> None:
    """Start K2 Deck web server if not already running.

    The subprocess is intentionally left running after MCP server exits.
    The is_alive() check prevents duplicate instances on restart.
    """
    client = get_client()
    if await client.is_alive():
        logger.info("K2 Deck web server already running on :8420")
        return

    logger.info("Starting K2 Deck web server...")
    subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from k2deck.web.server import run_server; run_server()",
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    # Wait up to 5s for server to come up
    for _ in range(50):
        await asyncio.sleep(0.1)
        if await client.is_alive():
            logger.info("K2 Deck web server started successfully")
            return

    raise RuntimeError("Failed to start K2 Deck web server on :8420")


# =============================================================================
# Main Entry Point
# =============================================================================


async def main() -> None:
    """Run the K2 Deck MCP server."""
    await ensure_web_server()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
