#!/usr/bin/env python3
"""Bulk-load URL sources into NotebookLM notebooks from a YAML manifest.

Reads scripts/sources.yaml (mapping: notebook title -> list of URLs).
For each notebook: looks it up by title (case-insensitive); creates if missing.
For each URL: skips if the same URL already exists as a source; otherwise adds
it with wait=True so the source is indexed before moving on.

Usage:
    python scripts/bulk_load.py [path/to/sources.yaml]

Requires:
    - notebooklm-py installed and `notebooklm login` already run
    - pyyaml (pip install pyyaml)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml

from notebooklm import NotebookLMClient, Notebook, RateLimitError, SourceAddError

DEFAULT_MANIFEST = Path(__file__).parent / "sources.yaml"
RATE_LIMIT_BACKOFF_SEC = 5.0


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _find_notebook(notebooks: list[Notebook], title: str) -> Notebook | None:
    target = title.strip().casefold()
    for nb in notebooks:
        if (nb.title or "").strip().casefold() == target:
            return nb
    return None


async def _add_with_retry(client: NotebookLMClient, notebook_id: str, url: str) -> str:
    """Add URL with one 5s retry on rate limit. Returns status string."""
    for attempt in (1, 2):
        try:
            await client.sources.add_url(notebook_id, url, wait=True)
            return "ok"
        except RateLimitError:
            if attempt == 1:
                print(f"      rate-limited; sleeping {RATE_LIMIT_BACKOFF_SEC:.0f}s and retrying...")
                await asyncio.sleep(RATE_LIMIT_BACKOFF_SEC)
                continue
            return "fail (rate limited after retry)"
        except SourceAddError as e:
            return f"fail ({e})"
        except Exception as e:  # noqa: BLE001 - surface unexpected errors as fail status
            return f"fail ({type(e).__name__}: {e})"
    return "fail (unknown)"


async def process_notebook(
    client: NotebookLMClient,
    all_notebooks: list[Notebook],
    title: str,
    urls: list[str],
) -> None:
    print(f"\n[NB] {title}")

    nb = _find_notebook(all_notebooks, title)
    if nb is None:
        print(f"  not found — creating...")
        nb = await client.notebooks.create(title)
        all_notebooks.append(nb)
        existing_urls: set[str] = set()
    else:
        print(f"  found  id={nb.id}")
        sources = await client.sources.list(nb.id)
        existing_urls = {_normalize_url(s.url) for s in sources if s.url}

    for url in urls:
        norm = _normalize_url(url)
        if norm in existing_urls:
            print(f"  [skip] {url}  (already a source)")
            continue

        print(f"  [+]   {url}")
        status = await _add_with_retry(client, nb.id, url)
        if status == "ok":
            existing_urls.add(norm)
            print(f"      ok")
        else:
            print(f"      {status}")


async def main(manifest_path: Path) -> int:
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest: dict[str, list[str]] = yaml.safe_load(f) or {}

    if not isinstance(manifest, dict):
        print(f"Manifest must be a mapping of notebook -> [urls]", file=sys.stderr)
        return 1

    print(f"Loading manifest: {manifest_path}")
    print(f"Notebooks in manifest: {len(manifest)}")

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        print(f"Found {len(notebooks)} notebooks in account")

        for title, urls in manifest.items():
            if not isinstance(urls, list):
                print(f"\n[NB] {title}\n  skipping — value is not a list of URLs")
                continue
            await process_notebook(client, notebooks, title, urls)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MANIFEST
    sys.exit(asyncio.run(main(path)))
