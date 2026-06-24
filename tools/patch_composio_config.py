#!/usr/bin/env python3
"""Patch the Hermes config to add Composio MCP server."""
import re

CONFIG_PATH = "C:/Users/dell-/AppData/Local/hermes/config.yaml"

with open(CONFIG_PATH, encoding="utf-8") as f:
    content = f.read()

# Check if composio already exists
if "composio" in content and "mcp_servers" in content:
    print("Composio MCP already configured!")
else:
    # Add composio after codegraph section
    old = """mcp_servers:
  codegraph:
    command: codegraph
    args:
    - serve
    - --mcp
    timeout: 120
    connect_timeout: 60
    enabled: true"""

    new = """mcp_servers:
  codegraph:
    command: codegraph
    args:
    - serve
    - --mcp
    timeout: 120
    connect_timeout: 60
    enabled: true
  composio:
    command: composio
    args:
    - serve
    - --port
    - "8643"
    timeout: 120
    connect_timeout: 60
    env:
      COMPOSIO_API_KEY: "***"
    enabled: true"""

    if old in content:
        content = content.replace(old, new)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("✓ Composio MCP adicionado ao config.yaml!")
        print("   Endpoint: localhost:8643")
        print("   Protocol: HTTP/SSE")
    else:
        print("✗ Could not find codegraph MCP config section")
        # Debug: find the mcp_servers section
        idx = content.find("mcp_servers:")
        if idx >= 0:
            print(f"Found at index {idx}")
            print(repr(content[idx:idx+400]))

# Verify after write
with open(CONFIG_PATH, encoding="utf-8") as f:
    content = f.read()

if "composio" in content and "mcp_servers" in content:
    print("\n✓ Verification: Composio section found in config!")
else:
    print("\n✗ Verification failed")
