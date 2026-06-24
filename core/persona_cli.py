#!/usr/bin/env python3
"""
persona — CRUD CLI (Manage persona traits)

Commands: create, read, update, delete, list

Usage:
  persona_cli create <title> [--description DESC]
  persona_cli read <id>
  persona_cli update <id> [--title T] [--description D]
  persona_cli delete <id>
  persona_cli list [--sort-by field]
"""

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
    print(f"Created item {item.id}: {item.title}")
    _next_id += 1
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    item = _find(args.id)
    if not item:
        print(f"Error: item {args.id} not found", file=sys.stderr)
        return 1
    print(f"ID:          {item.id}")
    print(f"Title:       {item.title}")
    print(f"Description: {item.description}")
    print(f"Created:     {item.created_at}")
    print(f"Updated:     {item.updated_at}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    item = _find(args.id)
    if not item:
        print(f"Error: item {args.id} not found", file=sys.stderr)
        return 1
    if args.title:
        item.title = args.title
    if args.description:
        item.description = args.description
    item.updated_at = datetime.now().isoformat()
    print(f"Updated item {item.id}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    item = _find(args.id)
    if not item:
        print(f"Error: item {args.id} not found", file=sys.stderr)
        return 1
    _store.remove(item)
    print(f"Deleted item {args.id}")
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
        print(f"  {item.id:>3}  {item.title}")
    return 0


# ── Parser ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="persona_cli",
        description="Manage persona traits",
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
