#!/usr/bin/env python3
"""
TokenJuice CLI — Wrapper para compressão de arquivos via terminal.
Uso: python token_juice_cli.py <arquivo>
     cat <arquivo> | python token_juice_cli.py
"""

import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

try:
    from token_juice import tokenjuice
except ImportError:
    # Fallback path
    sys.path.insert(0, str(Path.home() / "AppData/Local/hermes/lib"))
    from token_juice import tokenjuice


def main():
    content = None

    if len(sys.argv) > 1 and sys.argv[1] != "-":
        filepath = Path(sys.argv[1])
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
        else:
            print(f"Arquivo não encontrado: {filepath}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin (pipe)
        content = sys.stdin.read()

    if not content:
        print("Nada para comprimir.", file=sys.stderr)
        sys.exit(0)

    result = tokenjuice(content)

    if "--stats" in sys.argv:
        print(json.dumps({
            "original_chars": result["original_chars"],
            "compressed_chars": result["compressed_chars"],
            "original_lines": result["original_lines"],
            "compressed_lines": result["compressed_lines"],
            "savings_pct": result["savings_pct"],
            "layers": result["layers_applied"],
        }, indent=2))
    else:
        print(result["compressed"])
        if "--verbose" in sys.argv:
            print(f"\n--- TokenJuice: {result['savings_pct']}% economia ({result['original_chars']} → {result['compressed_chars']} chars) ---",
                  file=sys.stderr)


if __name__ == "__main__":
    main()