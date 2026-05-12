#!/usr/bin/env python3
"""Generate today's Azure DE audio brief and download it.

Picks a notebook based on the weekday, generates a deep-dive Audio Overview
with interview-focused instructions, polls every 30s for up to 15 min, then
downloads the MP3 to downloads/audio-briefs/YYYY-MM-DD-<slug>.mp3.

Usage:
    python scripts/daily_brief.py
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import date
from pathlib import Path

from notebooklm import AudioFormat, NotebookLMClient


def _report_auth_source() -> None:
    """Log which auth source from_storage() will pick up.

    Precedence inside the library is:
      1. NOTEBOOKLM_AUTH_JSON  (inline JSON, preferred for cloud routines)
      2. ~/.notebooklm/profiles/<profile>/storage_state.json  (local cookie file)
    """
    if os.environ.get("NOTEBOOKLM_AUTH_JSON"):
        size = len(os.environ["NOTEBOOKLM_AUTH_JSON"])
        print(f"Auth: NOTEBOOKLM_AUTH_JSON env var ({size:,} bytes)")
    else:
        profile = os.environ.get("NOTEBOOKLM_PROFILE", "default")
        home = os.environ.get("NOTEBOOKLM_HOME", str(Path.home() / ".notebooklm"))
        path = Path(home) / "profiles" / profile / "storage_state.json"
        if path.exists():
            print(f"Auth: file {path}")
        else:
            print(
                "ERROR: no NOTEBOOKLM_AUTH_JSON env var and no cookie file at "
                f"{path}. Run `notebooklm login` locally or set the env var.",
                file=sys.stderr,
            )
            sys.exit(1)

WEEKDAY_TO_NOTEBOOK = {
    0: "02 - Azure Data Factory",            # Monday
    1: "03 - Azure Databricks + PySpark",    # Tuesday
    2: "04 - Synapse + ADLS + Storage",      # Wednesday
    3: "05 - DP-203 + Architecture + Streaming",  # Thursday
    4: "07 - Git + CI-CD for DE",            # Friday
    5: "06 - Interview Bank",                # Saturday
    6: "01 - Foundations (SQL + Python + DW)",  # Sunday
}

INSTRUCTIONS = (
    "Focus on interview-relevant tradeoffs. Compare Azure services to AWS and "
    "Microsoft Fabric equivalents where relevant. Make it conversational and "
    "example-driven."
)

POLL_INTERVAL_SEC = 30.0
TIMEOUT_SEC = 15 * 60  # 15 minutes

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "downloads" / "audio-briefs"


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "notebook"


async def main() -> int:
    _report_auth_source()
    today = date.today()
    target_title = WEEKDAY_TO_NOTEBOOK[today.weekday()]
    print(f"Today is {today.isoformat()} ({today.strftime('%A')}) — target notebook: {target_title}")

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        nb = next(
            (n for n in notebooks if (n.title or "").strip().casefold() == target_title.casefold()),
            None,
        )
        if nb is None:
            print(f"ERROR: notebook not found by title: {target_title!r}", file=sys.stderr)
            print("Available notebooks:", file=sys.stderr)
            for n in notebooks:
                print(f"  - {n.title}", file=sys.stderr)
            return 1
        print(f"Notebook id: {nb.id}")

        print("Starting deep-dive audio generation...")
        gen = await client.artifacts.generate_audio(
            nb.id,
            instructions=INSTRUCTIONS,
            audio_format=AudioFormat.DEEP_DIVE,
        )
        task_id = gen.task_id
        print(f"  task_id: {task_id}")
        print(f"  polling every {POLL_INTERVAL_SEC:.0f}s, timeout {TIMEOUT_SEC // 60} min...")

        try:
            final = await client.artifacts.wait_for_completion(
                nb.id,
                task_id,
                initial_interval=POLL_INTERVAL_SEC,
                max_interval=POLL_INTERVAL_SEC,
                timeout=float(TIMEOUT_SEC),
            )
        except TimeoutError as e:
            print(f"ERROR: timeout waiting for audio: {e}", file=sys.stderr)
            return 2

        if final.is_failed:
            print(f"ERROR: generation failed: {final.error}", file=sys.stderr)
            return 1
        if not final.is_complete:
            print(f"ERROR: unexpected final status: {final.status}", file=sys.stderr)
            return 1

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{today.isoformat()}-{_slug(target_title)}.mp3"
        print(f"Downloading to {out_path}...")
        saved = await client.artifacts.download_audio(nb.id, str(out_path), artifact_id=task_id)

    size_mb = Path(saved).stat().st_size / (1024 * 1024)
    print(f"Done. {today.isoformat()} · {target_title} · {size_mb:.1f} MB → {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
