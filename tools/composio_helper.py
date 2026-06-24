#!/usr/bin/env python3
"""
Composio Helper — Interface with Composio SDK for Hermes Agent.
Uses API key from ~/.composio/api_key or COMPOSIO_API_KEY env var.

Usage:
  python composio_helper.py status       # Check connection status
  python composio_helper.py tools        # List available tools
  python composio_helper.py apps         # List available apps
  python composio_helper.py connect APP  # Connect an app (OAuth)
"""

import json
import os
import sys
from pathlib import Path

API_KEY_FILE = Path.home() / ".composio" / "api_key"


def get_api_key() -> str:
    """Get API key from env var or file."""
    key = os.environ.get("COMPOSIO_API_KEY")
    if key:
        return key
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text().strip()
    print("❌ API key not found. Set COMPOSIO_API_KEY or save to ~/.composio/api_key")
    sys.exit(1)


def cmd_status():
    """Check composio connection status."""
    key = get_api_key()
    print(f"✓ API Key: {key[:6]}...{key[-4:]}")
    
    try:
        from composio import Composio
        c = Composio(api_key=key)
        
        # Check connected accounts
        try:
            accounts = c.connected_accounts.get()
            print(f"  Connected accounts: {accounts}")
        except Exception as e:
            print(f"  Accounts: {e}")
        
        # List integrations
        try:
            if hasattr(c, 'integrations'):
                integrations = c.integrations.get()
                print(f"  Integrations: OK")
        except Exception as e:
            print(f"  Integrations: {e}")
            
        print(f"  SDK: composio v{__import__('composio').__version__}")
        
    except ImportError:
        print("❌ composio SDK not installed. Run: pip install composio")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)


def cmd_tools():
    """List available tools via Composio."""
    key = get_api_key()
    from composio import Composio
    c = Composio(api_key=key)
    try:
        tools = c.tools
        print(f"Tools available: {tools}")
    except Exception as e:
        print(f"Error listing tools: {e}")


def cmd_apps():
    """List available apps."""
    key = get_api_key()
    from composio import Composio
    c = Composio(api_key=key)
    try:
        apps = c.apps.get()
        if isinstance(apps, list):
            print(f"Available apps ({len(apps)}):")
            for app in apps[:30]:
                name = getattr(app, 'name', str(app))
                print(f"  • {name}")
        else:
            print(f"Apps: {apps}")
    except Exception as e:
        print(f"Error listing apps: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    commands = {
        "status": cmd_status,
        "tools": cmd_tools,
        "apps": cmd_apps,
    }
    
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()