#!/usr/bin/env python3
"""Run deep web research on a list of topic queries and import all results.

Reads scripts/research_queries.yaml (target notebook + list of queries).
For each query: starts a deep web research session, polls until it completes
(or times out), then imports every returned source into the target notebook.

Usage:
    python scripts/research_import.py [path/to/research_queries.yaml]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml

from notebooklm import NotebookLMClient

DEFAULT_MANIFEST = Path(__file__).parent / "research_queries.yaml"
POLL_INTERVAL_SEC = 30.0
PER_QUERY_TIMEOUT_SEC = 30 * 60  # 30 min


def _find_notebook(notebooks, title: str):
    target = title.strip().casefold()
    return next((n for n in notebooks if (n.title or "").strip().casefold() == target), None)


async def _wait_for_research(
    client: NotebookLMClient, notebook_id: str, task_id: str, timeout: float
) -> dict | None:
    """Poll research status until the matching task_id reports completed or timeout fires."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        result = await client.research.poll(notebook_id)
        tasks = result.get("tasks") or []
        for task in tasks:
            if task.get("task_id") == task_id and task.get("status") == "completed":
                return task
        elapsed = int(timeout - (deadline - loop.time()))
        print(f"      [{elapsed:>4}s] still in progress, sleeping {POLL_INTERVAL_SEC:.0f}s...")
        await asyncio.sleep(POLL_INTERVAL_SEC)

    return None


async def main(manifest_path: Path) -> int:
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    target_title = manifest.get("target_notebook")
    queries = manifest.get("queries") or []
    if not target_title or not queries:
        print("Manifest needs 'target_notebook' and 'queries' fields.", file=sys.stderr)
        return 1

    print(f"Target notebook : {target_title}")
    print(f"Queries         : {len(queries)}")
    print(f"Per-query budget: {PER_QUERY_TIMEOUT_SEC // 60} min")

    totals: dict[str, int] = {}

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        nb = _find_notebook(notebooks, target_title)
        if nb is None:
            print(f"ERROR: notebook not found: {target_title!r}", file=sys.stderr)
            return 1
        print(f"Notebook id     : {nb.id}\n")

        for i, query in enumerate(queries, 1):
            print(f"[{i}/{len(queries)}] {query}")
            try:
                task = await client.research.start(nb.id, query, source="web", mode="deep")
            except Exception as e:
                print(f"   start failed: {e}")
                totals[query] = -1
                continue

            if not task or not task.get("task_id"):
                print(f"   start returned no task_id; skipping")
                totals[query] = -1
                continue
            task_id = task["task_id"]
            print(f"   task_id: {task_id}  — waiting up to {PER_QUERY_TIMEOUT_SEC // 60} min...")

            completed = await _wait_for_research(client, nb.id, task_id, PER_QUERY_TIMEOUT_SEC)
            if completed is None:
                print(f"   timeout — moving on (research may finish in the background)")
                totals[query] = -2
                continue

            sources = completed.get("sources") or []
            print(f"   research complete — {len(sources)} sources found")

            if not sources:
                totals[query] = 0
                continue

            try:
                imported = await client.research.import_sources(nb.id, task_id, sources)
            except Exception as e:
                print(f"   import failed: {e}")
                totals[query] = -3
                continue

            print(f"   imported: {len(imported)} sources")
            totals[query] = len(imported)

    # Final summary
    print("\n=== Summary ===")
    for query, count in totals.items():
        if count >= 0:
            print(f"  ok  ({count:>2}): {query}")
        elif count == -1:
            print(f"  ERR (start/import failed): {query}")
        elif count == -2:
            print(f"  TMO (timeout): {query}")
        elif count == -3:
            print(f"  ERR (import failed): {query}")
    total_imported = sum(c for c in totals.values() if c > 0)
    print(f"\nTotal new sources imported: {total_imported}")
    return 0


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MANIFEST
    sys.exit(asyncio.run(main(path)))
