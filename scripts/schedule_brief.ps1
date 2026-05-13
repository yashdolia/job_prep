<#
.SYNOPSIS
    Register a Windows Scheduled Task to run daily_brief.py every morning at 7:00 AM.

.DESCRIPTION
    The task runs under the current user with logon type S4U, meaning it fires
    whether or not the user is interactively logged in (no stored password).
    Re-running this script overwrites any existing task of the same name.

.NOTES
    - NotebookLM auth cookies live under the current user's profile
      (~/.notebooklm/profiles/default/), so the task MUST run as the same user
      that ran `notebooklm login`. S4U preserves user identity.
    - If S4U fails on your machine (rare; some corporate AD policies block it),
      change LogonType to Password — that will prompt for your password on
      registration and store it in the credential vault.
    - View / edit / delete in Task Scheduler under Task Scheduler Library →
      "NotebookLM Daily Brief".
#>

[CmdletBinding()]
param(
    [string] $TaskName  = "NotebookLM Daily Brief",
    [string] $TaskTime  = "07:00",
    [string] $RepoRoot
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
}

$python  = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$script  = Join-Path $RepoRoot "scripts\daily_brief.py"
$wrapper = Join-Path $RepoRoot "scripts\run_with_preflight.ps1"

if (-not (Test-Path $python))  { throw "Python interpreter not found: $python" }
if (-not (Test-Path $script))  { throw "Script not found: $script" }
if (-not (Test-Path $wrapper)) { throw "Wrapper not found: $wrapper" }

$scriptName = Split-Path $script -Leaf

Write-Host "Registering scheduled task '$TaskName'"
Write-Host "  Wrapper: $wrapper"
Write-Host "  Script : $scriptName (gated by preflight auth check)"
Write-Host "  Trigger: every day at $TaskTime"
Write-Host "  WorkDir: $RepoRoot"

# Task fires the PS wrapper, which runs preflight_auth.py first and only
# invokes the Python script if auth is healthy. Toast notification on failure.
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapper`" -ScriptName `"$scriptName`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $TaskTime

# S4U = "Run whether user is logged on or not" without storing a password.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

# Idempotent: replace any existing task with the same name.
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Generate today's Azure DE audio brief from NotebookLM and download it." | Out-Null

Write-Host ""
Write-Host "Registered. Next run:" -ForegroundColor Green
Get-ScheduledTask -TaskName $TaskName |
    Get-ScheduledTaskInfo |
    Select-Object TaskName, NextRunTime, LastRunTime, LastTaskResult |
    Format-List

Write-Host "Manual run now : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Disable        : Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "Delete         : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
