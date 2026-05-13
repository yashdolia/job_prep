<#
.SYNOPSIS
    Run a job-prep script with a NotebookLM auth preflight check first.

.DESCRIPTION
    Invoked by Task Scheduler as a wrapper around daily_brief.py /
    quiz_to_anki.py. Runs preflight_auth.py first; if auth is expired or
    preflight otherwise fails, fires a Windows toast notification so the user
    sees the failure within seconds instead of weeks later.

    Exit codes mirror preflight: 0 success, 1 auth expired, 2 other preflight
    error, otherwise the target script's exit code.

.PARAMETER ScriptName
    Basename of the Python script under scripts/ to run after preflight passes.
    Example: daily_brief.py

.PARAMETER RepoRoot
    Optional override for the repo root. Defaults to parent of scripts/.

.PARAMETER PreflightTimeoutSec
    Seconds to wait for the preflight check before killing it. Default 60.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ScriptName,
    [string] $RepoRoot,
    [int]    $PreflightTimeoutSec = 60
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
    if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path
}

$python    = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$preflight = Join-Path $RepoRoot "scripts\preflight_auth.py"
$target    = Join-Path $RepoRoot ("scripts\" + $ScriptName)

function Show-Toast {
    param(
        [Parameter(Mandatory = $true)] [string] $Title,
        [Parameter(Mandatory = $true)] [string] $Message
    )
    try {
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]

        $template = @"
<toast><visual><binding template="ToastGeneric"><text>$Title</text><text>$Message</text></binding></visual></toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("NotebookLM Job Prep")
        $notifier.Show($toast)
        return $true
    } catch {
        Write-Warning "Toast failed: $($_.Exception.Message)"
        return $false
    }
}

function Write-Sentinel {
    param([Parameter(Mandatory = $true)] [string] $Reason)
    $sentinelDir = Join-Path $RepoRoot "downloads"
    if (-not (Test-Path $sentinelDir)) {
        New-Item -ItemType Directory -Path $sentinelDir -Force | Out-Null
    }
    $sentinel = Join-Path $sentinelDir "AUTH_EXPIRED.txt"
    "$(Get-Date -Format 'o') :: $Reason :: ScriptName=$ScriptName" |
        Out-File -FilePath $sentinel -Encoding utf8
}

if (-not (Test-Path $python))    { throw "Python interpreter not found: $python" }
if (-not (Test-Path $preflight)) { throw "Preflight script not found: $preflight" }
if (-not (Test-Path $target))    { throw "Target script not found: $target" }

Write-Host "[run_with_preflight] RepoRoot : $RepoRoot"
Write-Host "[run_with_preflight] Target   : $ScriptName"
Write-Host "[run_with_preflight] Preflight: starting (timeout ${PreflightTimeoutSec}s)..."

$proc = Start-Process -FilePath $python `
                      -ArgumentList @("`"$preflight`"") `
                      -WorkingDirectory $RepoRoot `
                      -NoNewWindow `
                      -PassThru
if (-not $proc.WaitForExit($PreflightTimeoutSec * 1000)) {
    try { $proc.Kill() } catch { }
    Write-Host "[run_with_preflight] Preflight TIMEOUT" -ForegroundColor Red
    $shown = Show-Toast -Title "NotebookLM preflight timeout" `
                        -Message "Preflight took longer than ${PreflightTimeoutSec}s. Skipping $ScriptName."
    if (-not $shown) { Write-Sentinel -Reason "preflight timeout" }
    exit 2
}

$preflightExit = $proc.ExitCode
Write-Host "[run_with_preflight] Preflight exit: $preflightExit"

if ($preflightExit -eq 1) {
    $shown = Show-Toast -Title "NotebookLM auth expired" `
                        -Message "Run 'notebooklm login' to re-authenticate. Skipped $ScriptName."
    if (-not $shown) { Write-Sentinel -Reason "auth expired" }
    exit 1
}
elseif ($preflightExit -ne 0) {
    $shown = Show-Toast -Title "NotebookLM preflight error" `
                        -Message "Preflight exited $preflightExit. Skipped $ScriptName."
    if (-not $shown) { Write-Sentinel -Reason "preflight error $preflightExit" }
    exit $preflightExit
}

Write-Host "[run_with_preflight] Preflight OK. Running $ScriptName..."
& $python $target
exit $LASTEXITCODE
