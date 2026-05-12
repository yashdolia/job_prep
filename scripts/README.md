# Automation Scripts — Azure DE Interview Prep

Custom scripts built on top of `notebooklm-py` to automate study workflows for the Azure Data Engineer (DP-203) interview prep notebooks.

> The other files in this folder (`check_rpc_health.py`, `diagnose_get_notebook.py`) belong to the upstream `notebooklm-py` project and are unrelated to these scripts.

## Target notebooks

| Notebook | Topic |
|---|---|
| `01 - Foundations (SQL + Python + DW)` | SQL, Python, data warehousing fundamentals |
| `02 - Azure Data Factory` | ADF pipelines, linked services, triggers |
| `03 - Azure Databricks + PySpark` | Databricks, PySpark, Delta Lake |
| `04 - Synapse + ADLS + Storage` | Synapse, ADLS Gen2, storage tiers |
| `05 - DP-203 + Architecture + Streaming` | Exam topics, architecture, Event Hubs / Stream Analytics |
| `06 - Interview Bank` | Aggregated Q&A, mock interviews |

## Scripts (planned)

### `bulk_load.py`
Bulk-add a list of URLs / local PDFs / YouTube links into a target notebook, then wait for all sources to reach `ready` before exiting. Input: a YAML or JSON manifest mapping notebook → list of source URIs.

**Goal:** seed each topic notebook with curated study material without clicking through the web UI.

### `daily_brief.py`
For each notebook, ask a fixed set of "what should I review today" questions and aggregate the answers into a single dated Markdown brief saved locally (and optionally as a note in `06 - Interview Bank`).

**Goal:** generate a one-page daily revision sheet across all six notebooks.

### `quiz_to_anki.py`
Run `generate quiz` (or `generate flashcards`) on a chosen notebook, download as JSON, and emit an Anki-importable `.txt` (tab-separated `front\tback\ttags`) for spaced-repetition study.

**Goal:** turn NotebookLM-generated quizzes into Anki decks per topic.

### `research_import.py`
Kick off `source add-research --mode deep --no-wait` for a list of topic queries against `06 - Interview Bank`, then poll `research wait --import-all` and report how many sources landed per query.

**Goal:** broaden the interview bank with fresh web research on weak topics, hands-off.

## Conventions

- All scripts use the async client (`NotebookLMClient.from_storage()`).
- Notebook IDs are passed explicitly via CLI flag — no reliance on `notebooklm use` context (parallel-safe).
- Output written under `./out/` (gitignored) by default; pass `--out <dir>` to override.
- Read credentials/profile from the standard `~/.notebooklm/profiles/<profile>/storage_state.json`; respect `NOTEBOOKLM_PROFILE` env var.
- Long-running operations log progress and exit with code `2` on timeout, `1` on API error, `0` on success.
