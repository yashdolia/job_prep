#!/usr/bin/env python3
"""Generate a DP-203 quiz from NotebookLM and convert to an Anki CSV deck.

- Source notebook: "05 - DP-203 + Architecture + Streaming"
- Quiz: HARD difficulty, MORE quantity
- JSON dumped to downloads/quizzes/
- Anki CSV (Front, Back) dumped to downloads/anki-decks/dp203-YYYY-MM-DD.csv

Usage:
    python scripts/quiz_to_anki.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import string
import sys
from datetime import date
from pathlib import Path

from notebooklm import NotebookLMClient, QuizDifficulty, QuizQuantity

NOTEBOOK_TITLE = "05 - DP-203 + Architecture + Streaming"
POLL_INTERVAL_SEC = 30.0
TIMEOUT_SEC = 15 * 60

REPO_ROOT = Path(__file__).resolve().parents[1]
QUIZ_DIR = REPO_ROOT / "downloads" / "quizzes"
ANKI_DIR = REPO_ROOT / "downloads" / "anki-decks"


def _find_notebook(notebooks, title: str):
    target = title.casefold().strip()
    return next((n for n in notebooks if (n.title or "").strip().casefold() == target), None)


def _quiz_to_anki_rows(questions: list[dict]) -> list[tuple[str, str]]:
    """Return (front, back) tuples ready for csv writer."""
    rows: list[tuple[str, str]] = []
    letters = string.ascii_uppercase

    for q in questions:
        question_text = (q.get("question") or "").strip()
        options = q.get("answerOptions") or []

        labeled = []
        correct_letters: list[str] = []
        for i, opt in enumerate(options):
            if i >= len(letters):
                break
            letter = letters[i]
            text = (opt.get("text") or "").strip()
            labeled.append(f"{letter}. {text}")
            if opt.get("isCorrect"):
                correct_letters.append(letter)

        front = question_text + "\n\n" + "\n".join(labeled)

        # Hint is the only explanation-like field NotebookLM emits for quizzes;
        # use it as the back-side rationale when available.
        explanation = (q.get("hint") or "").strip()
        correct_str = ", ".join(correct_letters) if correct_letters else "(no correct answer flagged)"
        back = f"Answer: {correct_str}"
        if explanation:
            back += f"\n\n{explanation}"

        rows.append((front, back))
    return rows


async def main() -> int:
    today = date.today().isoformat()

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        nb = _find_notebook(notebooks, NOTEBOOK_TITLE)
        if nb is None:
            print(f"ERROR: notebook not found: {NOTEBOOK_TITLE!r}", file=sys.stderr)
            return 1
        print(f"Notebook: {nb.title}  (id={nb.id})")

        print("Generating HARD quiz (quantity=MORE)...")
        gen = await client.artifacts.generate_quiz(
            nb.id,
            difficulty=QuizDifficulty.HARD,
            quantity=QuizQuantity.MORE,
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
            print(f"ERROR: timeout waiting for quiz: {e}", file=sys.stderr)
            return 2

        if final.is_failed:
            print(f"ERROR: generation failed: {final.error}", file=sys.stderr)
            return 1
        if not final.is_complete:
            print(f"ERROR: unexpected final status: {final.status}", file=sys.stderr)
            return 1

        QUIZ_DIR.mkdir(parents=True, exist_ok=True)
        json_path = QUIZ_DIR / f"dp203-{today}.json"
        print(f"Downloading quiz JSON to {json_path}...")
        await client.artifacts.download_quiz(
            nb.id, str(json_path), artifact_id=task_id, output_format="json"
        )

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    questions = payload.get("questions") or []
    if not questions:
        print("ERROR: downloaded quiz has no questions", file=sys.stderr)
        return 1

    rows = _quiz_to_anki_rows(questions)

    ANKI_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = ANKI_DIR / f"dp203-{today}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        # QUOTE_ALL so Anki imports multi-line Fronts/Backs cleanly
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Front", "Back"])
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} cards to {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
