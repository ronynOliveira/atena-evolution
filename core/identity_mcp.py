#!/usr/bin/env python3
"""
identity-mcp — MCP Server (Identity management MCP server)

MCP (Model Context Protocol) server providing tools and resources.
Compatible with MCP clients (Claude Desktop, Hermes Agent, etc.)

Run:
  identity-mcp            # stdio mode (for MCP client integration)
  identity-mcp --sse      # SSE mode (HTTP server)

Dependencies:
  pip install mcp
"""

import argparse
import sys
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        ListResourcesRequest,
        ListToolsRequest,
        ReadResourceRequest,
        Resource,
        TextContent,
        Tool,
    )
except ImportError:
    print(
        "Error: 'mcp' package not found. Install with: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)


# ── MCP Server Definition ─────────────────────────────────────────────────

server = Server("identity-mcp")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Register the tools this server provides."""
    return [
        Tool(
            name="greet",
            description="Greet someone by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the person to greet",
                    },
                    "enthusiasm": {
                        "type": "integer",
                        "description": "Enthusiasm level (1-10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="echo",
            description="Echo back the input message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back",
                    },
                },
                "required": ["message"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(req: CallToolRequest) -> list[TextContent]:
    """Dispatch tool calls."""
    name = req.params.name
    args = req.params.arguments or {}

    if name == "greet":
        greeting = args.get("name", "world")
        level = args.get("enthusiasm", 5)
        punctuation = "!" * min(level, 10)
        return [TextContent(type="text", text=f"Hello, {greeting}{punctuation}")]

    elif name == "echo":
        msg = args.get("message", "")
        return [TextContent(type="text", text=msg)]

    else:
        raise ValueError(f"Unknown tool: {name}")


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """Register resources (data that can be read)."""
    return [
        Resource(
            uri="identity_mcp://info/version",
            name="Version Info",
            description="Server version information",
            mimeType="text/plain",
        ),
        Resource(
            uri="identity_mcp://info/health",
            name="Health Check",
            description="Server health status",
            mimeType="text/plain",
        ),
    ]


@server.read_resource()
async def handle_read_resource(req: ReadResourceRequest) -> str:
    """Return resource content."""
    uri = req.params.uri

    if uri == "identity_mcp://info/version":
        return "{name} MCP Server v{version}"
    elif uri == "identity_mcp://info/health":
        return "status: ok"

    raise ValueError(f"Unknown resource: {uri}")


# ── CLI Entry Point ───────────────────────────────────────────────────────

def run_server(sse: bool = False, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the MCP server in stdio or SSE mode."""
    import asyncio

    async def _run_stdio():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    async def _run_sse():
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        import uvicorn

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as (read, write):
                await server.run(
                    read, write, server.create_initialization_options()
                )

        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server_instance = uvicorn.Server(config)
        await server_instance.serve()

    if sse:
        asyncio.run(_run_sse())
    else:
        asyncio.run(_run_stdio())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="identity-mcp",
        description="Identity management MCP server",
    )
    parser.add_argument("--sse", action="store_true",
                        help="Run in SSE (HTTP) mode instead of stdio")
    parser.add_argument("--host", default="127.0.0.1",
                        help="SSE host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000,
                        help="SSE port (default: 8000)")
    args = parser.parse_args(argv)

    run_server(sse=args.sse, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
