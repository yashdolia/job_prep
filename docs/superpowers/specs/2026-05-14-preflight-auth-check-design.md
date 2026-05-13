# Preflight Auth Check for Scheduled Tasks

**Date:** 2026-05-14
**Status:** Approved, ready to implement

## Problem

`daily_brief.py` and `quiz_to_anki.py` run via Windows Task Scheduler at 7:00 AM
daily / 8:00 AM Sundays. When NotebookLM cookies expire (IP-bound, unpredictable
TTL), both scripts crash with a `ValueError` traceback. Task Scheduler records a
nonzero exit code but surfaces nothing to the user. Failures can go unnoticed
for weeks — exactly happened on 2026-05-13 when the quiz pipeline failed
silently the first time it was attempted under a scheduler.

## Goal

Catch expired auth (and other startup errors) **before** the long-running NotebookLM
API call, and fire a Windows toast notification so the user sees the failure
within seconds, not weeks.

## Non-Goals

- Auto-renewing auth (cookies require interactive Google sign-in).
- Validating notebook contents, venv health, or disk space (YAGNI — add when
  those failure modes appear).
- Retrying the underlying scripts.
- Email or push notifications.

## Architecture

```
Task Scheduler fires
        │
        ▼
run_with_preflight.ps1  ── -ScriptName daily_brief.py
        │
        ├─► python.exe preflight_auth.py
        │       │
        │       ├─ exit 0  → continue
        │       ├─ exit 1  → Show-Toast "Auth expired — run 'notebooklm login'"  → exit 1
        │       └─ exit 2  → Show-Toast "Preflight error — see log"              → exit 2
        │
        └─► python.exe <target script>   (only reached on preflight exit 0)
                │
                └─ propagate exit code
```

## Components

### `scripts/preflight_auth.py`

Cheap auth check via one `client.notebooks.list()` call. Catches the exact
`ValueError("Authentication expired...")` raised by `notebooklm.auth` and
distinguishes it from generic errors via exit code.

| Exit code | Meaning              | Trigger                                                |
|-----------|----------------------|--------------------------------------------------------|
| 0         | OK                   | `notebooks.list()` returned successfully                |
| 1         | Auth expired         | `ValueError` containing "Authentication expired" or "Redirected to" |
| 2         | Other preflight error| Any other exception (network, RPC change, etc.)         |

### `scripts/run_with_preflight.ps1`

PowerShell wrapper. Accepts `-ScriptName <basename>` (e.g. `daily_brief.py`).
Resolves repo root, runs preflight, fires toast on failure, runs target on
success. Propagates exit codes.

Toast mechanism: `Windows.UI.Notifications.ToastNotificationManager` loaded via
`[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]`.
No third-party PowerShell modules required (BurntToast not needed).

Fallback if toast fails: write `downloads/AUTH_EXPIRED.txt` sentinel.

Preflight timeout: 60s. If exceeded → kill the python process, toast
"preflight timeout", exit 2.

### `scripts/schedule_brief.ps1` and `scripts/schedule_anki.ps1`

Single edit to `$action` block: instead of invoking `python.exe <script>`,
invoke `powershell.exe -File run_with_preflight.ps1 -ScriptName <script>`.

Both files are already idempotent (unregister + re-register), so re-running
them once after the change is the upgrade path.

## Failure Mode Mapping

| Real failure                                  | Preflight detects?       | User sees                                  |
|-----------------------------------------------|--------------------------|--------------------------------------------|
| Cookies expired (today's failure)             | ✅ exit 1                 | Toast: "Auth expired — run notebooklm login" |
| Network down at run time                      | ✅ exit 2                 | Toast: "Preflight error"                   |
| RPC method ID changed (library breaks)        | ✅ exit 2                 | Toast: "Preflight error"                   |
| `.venv` missing or python.exe gone            | ❌ wrapper fails first    | Task Scheduler exit code only (acceptable) |
| Audio generation timeout (Hindi-style)        | ❌ runs after preflight   | Same as today — Python exits nonzero       |
| Disk full mid-download                        | ❌ runs after preflight   | Same as today                              |

Scope is deliberately narrow: preflight catches the startup failures we've
actually seen.

## Testing

Manual only — the bug manifests only against real Google auth state.

1. **Healthy:** run `run_with_preflight.ps1 -ScriptName daily_brief.py` directly,
   confirm target script runs.
2. **Expired auth:** temporarily rename
   `~/.notebooklm/profiles/default/storage_state.json` → run wrapper → confirm
   toast appears, exit code 1, target script NOT invoked.
3. **Restore** storage_state.json, re-run healthy test.

Mocking real auth would test mocks, not the failure mode.

## Rollout

1. Land all three files.
2. Re-run `schedule_brief.ps1` and `schedule_anki.ps1` to re-register the
   scheduled tasks pointing at the wrapper.
3. Verify next-run-time in Task Scheduler matches expectation.
