"""Entry point for K2 Deck MCP server: python -m k2deck.mcp"""

import asyncio

from k2deck.mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())
