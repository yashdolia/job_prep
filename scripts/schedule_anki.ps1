<#
.SYNOPSIS
    Register a Windows Scheduled Task to run quiz_to_anki.py every Sunday at 8:00 AM.

.DESCRIPTION
    Generates a HARD DP-203 quiz from NotebookLM, converts it to an Anki-importable
    CSV, and saves it under downloads/anki-decks/. Re-running this script overwrites
    any existing task of the same name.

    Logon type S4U — runs whether or not the user is interactively logged in, no
    stored password. -WakeToRun is set so the system wakes from sleep at 8 AM.

.NOTES
    Must be run from an elevated (administrator) PowerShell window because S4U +
    WakeToRun require it.

    To make WakeToRun actually wake the laptop, also enable wake timers in the
    active power plan:
        powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
        powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
        powercfg /SETACTIVE SCHEME_CURRENT
#>

[CmdletBinding()]
param(
    [string] $TaskName  = "NotebookLM Weekly Anki Deck",
    [string] $TaskTime  = "08:00",
    [string] $DayOfWeek = "Sunday",
    [string] $RepoRoot
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
}

$python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$script = Join-Path $RepoRoot "scripts\quiz_to_anki.py"

if (-not (Test-Path $python)) { throw "Python interpreter not found: $python" }
if (-not (Test-Path $script)) { throw "Script not found: $script" }

Write-Host "Registering scheduled task '$TaskName'"
Write-Host "  Python : $python"
Write-Host "  Script : $script"
Write-Host "  Trigger: every $DayOfWeek at $TaskTime"
Write-Host "  WorkDir: $RepoRoot"

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "`"$script`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $TaskTime

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
    -Description "Generate a weekly DP-203 quiz from NotebookLM and convert it to an Anki CSV deck." | Out-Null

Write-Host ""
Write-Host "Registered. Next run:" -ForegroundColor Green
Get-ScheduledTask -TaskName $TaskName |
    Get-ScheduledTaskInfo |
    Select-Object TaskName, NextRunTime, LastRunTime, LastTaskResult |
    Format-List

Write-Host "Manual run now : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Disable        : Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "Delete         : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
