#!/usr/bin/env python3
"""
CLI Printing Press — boilerplate CLI & MCP server generator.

Usage:
  cli-printing-press MyTool                     # basic argparse CLI (default)
  cli-printing-press MyTool --pattern crud       # CRUD CLI template
  cli-printing-press MyTool --pattern search     # search/filter CLI template
  cli-printing-press MyTool --pattern mcp-server # MCP server template
  cli-printing-press MyTool --output-dir ./out   # write to specific dir
  cli-printing-press MyTool --stdout              # print to stdout only
  cli-printing-press --list-patterns              # list available patterns
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

# ── Template definitions ──────────────────────────────────────────────────

TEMPLATES: dict[str, dict[str, str]] = {}

TEMPLATES["cli"] = {
    "description": "Basic argparse CLI with subcommands",
    "ext": "py",
    "body": """\
#!/usr/bin/env python3
\"\"\"
{name} — {desc}

Usage:
  {snake}_cli <command> [options]
  {snake}_cli --help
\"\"\"

import argparse
import sys


def cmd_hello(args: argparse.Namespace) -> int:
    \"\"\"Say hello to the user.\"\"\"
    target = args.name or "world"
    print(f"Hello, {{target}}!")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    \"\"\"Print version.\"\"\"
    print("{name} v{version}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="{snake}_cli",
        description="{desc}",
    )
    parser.add_argument(
        "-v", "--version",
        action="store_true",
        help="show version and exit",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── hello ──────────────────────────────────────────────────────────────
    hello_p = sub.add_parser("hello", help="Say hello")
    hello_p.add_argument("-n", "--name", help="Who to greet")
    hello_p.set_defaults(func=cmd_hello)

    # ── version ────────────────────────────────────────────────────────────
    ver_p = sub.add_parser("version", help="Show version")
    ver_p.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "version", False):
        cmd_version(args)
        return 0

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
""",
}


TEMPLATES["crud"] = {
    "description": "CRUD CLI with in-memory data store",
    "ext": "py",
    "body": """\
#!/usr/bin/env python3
\"\"\"
{name} — CRUD CLI ({desc})

Commands: create, read, update, delete, list

Usage:
  {snake}_cli create <title> [--description DESC]
  {snake}_cli read <id>
  {snake}_cli update <id> [--title T] [--description D]
  {snake}_cli delete <id>
  {snake}_cli list [--sort-by field]
\"\"\"

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ── In-memory store ───────────────────────────────────────────────────────

@dataclass
class Item:
    id: int
    title: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


_store: list[Item] = []
_next_id: int = 1


def _find(item_id: int) -> Item | None:
    return next((i for i in _store if i.id == item_id), None)


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_create(args: argparse.Namespace) -> int:
    global _next_id
    item = Item(id=_next_id, title=args.title, description=args.description or "")
    _store.append(item)
    print(f"Created item {{item.id}}: {{item.title}}")
    _next_id += 1
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    item = _find(args.id)
    if not item:
        print(f"Error: item {{args.id}} not found", file=sys.stderr)
        return 1
    print(f"ID:          {{item.id}}")
    print(f"Title:       {{item.title}}")
    print(f"Description: {{item.description}}")
    print(f"Created:     {{item.created_at}}")
    print(f"Updated:     {{item.updated_at}}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    item = _find(args.id)
    if not item:
        print(f"Error: item {{args.id}} not found", file=sys.stderr)
        return 1
    if args.title:
        item.title = args.title
    if args.description:
        item.description = args.description
    item.updated_at = datetime.now().isoformat()
    print(f"Updated item {{item.id}}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    item = _find(args.id)
    if not item:
        print(f"Error: item {{args.id}} not found", file=sys.stderr)
        return 1
    _store.remove(item)
    print(f"Deleted item {{args.id}}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if not _store:
        print("No items.")
        return 0
    items = sorted(
        _store,
        key=lambda i: getattr(i, args.sort_by or "id"),
    )
    for item in items:
        print(f"  {{item.id:>3}}  {{item.title}}")
    return 0


# ── Parser ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="{snake}_cli",
        description="{desc}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="Create a new item")
    p.add_argument("title", help="Item title")
    p.add_argument("--description", "-d", help="Item description")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("read", help="Read an item by ID")
    p.add_argument("id", type=int, help="Item ID")
    p.set_defaults(func=cmd_read)

    p = sub.add_parser("update", help="Update an item")
    p.add_argument("id", type=int, help="Item ID")
    p.add_argument("--title", "-t", help="New title")
    p.add_argument("--description", "-d", help="New description")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete an item")
    p.add_argument("id", type=int, help="Item ID")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("list", help="List all items")
    p.add_argument("--sort-by", choices=["id", "title", "created_at"], default="id")
    p.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
""",
}


TEMPLATES["search"] = {
    "description": "Search/filter CLI with file or stdin input",
    "ext": "py",
    "body": """\
#!/usr/bin/env python3
\"\"\"
{name} — Search CLI ({desc})

Search through input (file or stdin) with filters, patterns, and output control.

Usage:
  {snake}_cli <pattern> [<file> ...]
  cat data.txt | {snake}_cli <pattern>
  {snake}_cli <pattern> --invert --context 2
  {snake}_cli <pattern> --count --file-list
\"\"\"

import argparse
import re
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="{snake}_cli",
        description="{desc}",
    )
    parser.add_argument("pattern", help="Search pattern (regex)")
    parser.add_argument("files", nargs="*", metavar="FILE",
                        help="Input files (default: stdin)")
    parser.add_argument("--invert", "-v", action="store_true",
                        help="Invert match (show non-matching lines)")
    parser.add_argument("--ignore-case", "-i", action="store_true",
                        help="Case-insensitive matching")
    parser.add_argument("--count", "-c", action="store_true",
                        help="Show match count per file instead of lines")
    parser.add_argument("--context", "-C", type=int, default=0,
                        help="Lines of context around each match")
    parser.add_argument("--file-list", "-l", action="store_true",
                        help="List matching filenames only")
    parser.add_argument("--no-filename", action="store_true",
                        help="Suppress filename prefix on single file")
    parser.add_argument("--color", choices=["auto", "always", "never"],
                        default="auto", help="Highlight matches")

    args = parser.parse_args(argv)

    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        pattern = re.compile(args.pattern, flags)
    except re.error as e:
        print(f"Invalid regex: {{e}}", file=sys.stderr)
        return 1

    sources = args.files or ["-"]
    use_color = (args.color == "always" or
                 (args.color == "auto" and sys.stdout.isatty()))
    total_exit = 0

    for src in sources:
        if src == "-":
            fh = sys.stdin
            show_fn = len(sources) > 2 and not args.no_filename
            fn = "<stdin>"
        else:
            p = Path(src)
            if not p.exists():
                print(f"Error: {{src}} not found", file=sys.stderr)
                total_exit = 1
                continue
            fh = p.open()
            show_fn = len(sources) > 1 and not args.no_filename
            fn = src

        count = 0
        matched_lines: list[tuple[int, str, bool]] = []
        context_buffer: list[tuple[int, str]] = []
        context_remaining = 0

        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\\n")
            is_match = bool(pattern.search(line))
            if args.invert:
                is_match = not is_match

            if args.file_list and is_match:
                print(fn)
                count = 1
                break

            if is_match:
                # emit any buffered context lines
                for ctx_ln, ctx_line in context_buffer:
                    matched_lines.append((ctx_ln, ctx_line, False))
                context_buffer.clear()
                matched_lines.append((lineno, line, True))
                count += 1
                context_remaining = args.context
            elif context_remaining > 0:
                matched_lines.append((lineno, line, False))
                context_remaining -= 1
            else:
                context_buffer.append((lineno, line))
                if len(context_buffer) > args.context:
                    context_buffer.pop(0)

        if args.file_list:
            if count == 0 and not args.invert:
                total_exit = 1
            continue

        if args.count:
            prefix = f"{{fn}}:" if show_fn else ""
            print(f"{{prefix}}{{count}}")
        else:
            for ln, text, highlight in matched_lines:
                prefix = f"{{fn}}:{{ln}}:" if show_fn else f"{{ln}}:"
                if use_color and highlight:
                    print(f"\\033[31m{{prefix}}\\033[0m{{text}}")
                else:
                    print(f"{{prefix}}{{text}}")

        if src != "-":
            fh.close()

        if args.count and count == 0 and not args.invert:
            total_exit = 1

    if args.file_list and total_exit == 0:
        # --file-list exits 0 even with zero matches
        pass

    return total_exit


if __name__ == "__main__":
    sys.exit(main())
""",
}


TEMPLATES["mcp-server"] = {
    "description": "MCP (Model Context Protocol) server with tools & resources",
    "ext": "py",
    "body": """\
#!/usr/bin/env python3
\"\"\"
{name} — MCP Server ({desc})

MCP (Model Context Protocol) server providing tools and resources.
Compatible with MCP clients (Claude Desktop, Hermes Agent, etc.)

Run:
  {kebab}            # stdio mode (for MCP client integration)
  {kebab} --sse      # SSE mode (HTTP server)

Dependencies:
  pip install mcp
\"\"\"

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

server = Server("{kebab}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    \"\"\"Register the tools this server provides.\"\"\"
    return [
        Tool(
            name="greet",
            description="Greet someone by name",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "name": {{
                        "type": "string",
                        "description": "Name of the person to greet",
                    }},
                    "enthusiasm": {{
                        "type": "integer",
                        "description": "Enthusiasm level (1-10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    }},
                }},
                "required": ["name"],
            }},
        ),
        Tool(
            name="echo",
            description="Echo back the input message",
            inputSchema={{
                "type": "object",
                "properties": {{
                    "message": {{
                        "type": "string",
                        "description": "Message to echo back",
                    }},
                }},
                "required": ["message"],
            }},
        ),
    ]


@server.call_tool()
async def handle_call_tool(req: CallToolRequest) -> list[TextContent]:
    \"\"\"Dispatch tool calls.\"\"\"
    name = req.params.name
    args = req.params.arguments or {{}}

    if name == "greet":
        greeting = args.get("name", "world")
        level = args.get("enthusiasm", 5)
        punctuation = "!" * min(level, 10)
        return [TextContent(type="text", text=f"Hello, {{greeting}}{{punctuation}}")]

    elif name == "echo":
        msg = args.get("message", "")
        return [TextContent(type="text", text=msg)]

    else:
        raise ValueError(f"Unknown tool: {{name}}")


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    \"\"\"Register resources (data that can be read).\"\"\"
    return [
        Resource(
            uri="{snake}://info/version",
            name="Version Info",
            description="Server version information",
            mimeType="text/plain",
        ),
        Resource(
            uri="{snake}://info/health",
            name="Health Check",
            description="Server health status",
            mimeType="text/plain",
        ),
    ]


@server.read_resource()
async def handle_read_resource(req: ReadResourceRequest) -> str:
    \"\"\"Return resource content.\"\"\"
    uri = req.params.uri

    if uri == "{snake}://info/version":
        return "{{name}} MCP Server v{{version}}"
    elif uri == "{snake}://info/health":
        return "status: ok"

    raise ValueError(f"Unknown resource: {{uri}}")


# ── CLI Entry Point ───────────────────────────────────────────────────────

def run_server(sse: bool = False, host: str = "127.0.0.1", port: int = 8000) -> None:
    \"\"\"Run the MCP server in stdio or SSE mode.\"\"\"
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
        prog="{kebab}",
        description="{desc}",
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
""",
}

# ── Template rendering ────────────────────────────────────────────────────

def to_snake(name: str) -> str:
    """Convert CamelCase/PascalCase to snake_case."""
    s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower().replace("-", "_").replace(" ", "_")


def to_camel(name: str) -> str:
    """Convert snake_case/kebab-case to PascalCase."""
    return "".join(w.capitalize() for w in re.split(r"[-_ ]", name))


def to_kebab(name: str) -> str:
    """Convert PascalCase/snake_case to kebab-case."""
    return to_snake(name).replace("_", "-")


def render_template(name: str, pattern: str, version: str, desc: str) -> str:
    """Fill in template variables."""
    tpl = TEMPLATES[pattern]["body"]
    snake = to_snake(name)
    kebab = to_kebab(name)
    server_name = kebab
    return tpl.format(
        name=name,
        snake=snake,
        kebab=kebab,
        server_name=server_name,
        version=version,
        desc=desc,
    )


# ── Main ──────────────────────────────────────────────────────────────────

def list_patterns() -> None:
    """Display available templates."""
    print("Available CLI Printing Press patterns:")
    print()
    for key, tpl in sorted(TEMPLATES.items()):
        print(f"  {key:<14}  {tpl['description']}")
    print()
    print("Use: cli-printing-press <NAME> --pattern <pattern>")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cli-printing-press",
        description="Generate boilerplate CLI and MCP server code.",
    )
    parser.add_argument("name", nargs="?",
                        help="Name of the tool/project (PascalCase or snake_case)")
    parser.add_argument("--pattern", "-p",
                        choices=list(TEMPLATES),
                        default="cli",
                        help="Template pattern to use (default: cli)")
    parser.add_argument("--version", "-V",
                        default="0.1.0",
                        help="Version string (default: 0.1.0)")
    parser.add_argument("--description", "-d",
                        default="A CLI tool",
                        help="Short description (default: 'A CLI tool')")
    parser.add_argument("--output-dir", "-o",
                        default=".",
                        help="Output directory (default: current directory)")
    parser.add_argument("--stdout", action="store_true",
                        help="Print generated code to stdout instead of a file")
    parser.add_argument("--list-patterns", action="store_true",
                        help="List available patterns and exit")

    args = parser.parse_args()

    if args.list_patterns:
        list_patterns()
        return 0

    if not args.name:
        parser.print_help()
        return 1

    code = render_template(args.name, args.pattern, args.version, args.description)
    snake = to_snake(args.name)
    ext = TEMPLATES[args.pattern]["ext"]
    suffix_map = {"mcp-server": "", "cli": "_cli", "crud": "_cli", "search": "_cli"}
    suffix = suffix_map.get(args.pattern, "_cli")
    filename = f"{snake}{suffix}.{ext}"

    if args.stdout:
        print(code)
        return 0

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    out_path.write_text(code)
    print(f"Generated: {out_path.resolve()}")
    print(f"Pattern:   {args.pattern} — {TEMPLATES[args.pattern]['description']}")
    print(f"Run with:  python {filename} --help")
    return 0


if __name__ == "__main__":
    sys.exit(main())