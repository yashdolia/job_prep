#!/usr/bin/env python3
"""Cheap NotebookLM auth check for scheduled tasks.

Exit codes:
    0 - OK, auth works
    1 - Auth expired or invalid (user must run `notebooklm login`)
    2 - Other preflight failure (network, RPC, etc.)

Usage:
    python scripts/preflight_auth.py
"""

from __future__ import annotations

import asyncio
import sys

from notebooklm import NotebookLMClient


async def main() -> int:
    try:
        async with await NotebookLMClient.from_storage() as client:
            await client.notebooks.list()
    except ValueError as e:
        msg = str(e)
        if "Authentication expired" in msg or "Redirected to" in msg:
            print(f"AUTH_EXPIRED: {msg}", file=sys.stderr)
            return 1
        print(f"PREFLIGHT_ERROR: {msg}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"PREFLIGHT_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
