<#
Watch the local skill checkout and commit/push changes to origin/main.

Install for the current Windows user:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\auto_sync.ps1 -InstallTask

Run once (useful for an already changed checkout):
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\auto_sync.ps1 -Once

The watcher only operates on this checkout's main branch. It never force-pushes,
resets, deletes files, or resolves a remote conflict automatically.
#>
[CmdletBinding()]
param(
    [switch]$InstallTask,
    [switch]$UninstallTask,
    [switch]$Once,
    [int]$DebounceSeconds = 4
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$TaskName = 'Codex brand-product-map auto-sync'
$LogPath = Join-Path $env:LOCALAPPDATA 'brand-product-map-auto-sync.log'
$scriptPath = (Resolve-Path $PSCommandPath).Path

function Write-Log([string]$Message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') $Message"
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Output $line
}

function Invoke-Git([string[]]$Arguments) {
    Push-Location $RepoRoot
    $oldErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $result = @(& git @Arguments 2>&1)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorAction
        Pop-Location
    }
    if ($code -ne 0) {
        $text = ($result -join [Environment]::NewLine).Trim()
        throw "git $($Arguments -join ' ') failed ($code): $text"
    }
    return $result
}

function Test-ChangedPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    $full = [IO.Path]::GetFullPath($Path)
    $gitDir = [IO.Path]::GetFullPath((Join-Path $RepoRoot '.git'))
    if ($full.StartsWith($gitDir + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { return $false }
    return $full.StartsWith($RepoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
}

function Sync-Now {
    Push-Location $RepoRoot
    try {
        $branch = ((Invoke-Git @('branch', '--show-current')) -join '').Trim()
        if ($branch -ne 'main') { throw "STOP: current branch is '$branch'; auto-sync only allows main" }
        $status = @(Invoke-Git @('status', '--porcelain', '--untracked-files=all'))
        if ($status.Count -eq 0) {
            Write-Log 'No local changes; nothing to commit.'
            return
        }
        Invoke-Git @('add', '--all', '--', '.') | Out-Null
        $null = & git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Log 'Changes were ignored or produced no staged diff.'
            return
        }
        $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'
        Invoke-Git @('commit', '-m', "auto-sync: brand-product-map ($stamp)") | ForEach-Object { Write-Log "$_" }
        Invoke-Git @('push', 'origin', 'main') | ForEach-Object { Write-Log "$_" }
        Write-Log 'SYNC OK: commit pushed to origin/main.'
    } catch {
        Write-Log "STOP: $($_.Exception.Message)"
    } finally {
        Pop-Location
    }
}

if ($InstallTask) {
    $taskCommand = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
    & schtasks.exe /Create /F /SC ONLOGON /TN $TaskName /TR $taskCommand /RL LIMITED | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Could not register scheduled task '$TaskName'" }
    Write-Log "Installed scheduled task '$TaskName'."
    $watchArgs = @('-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath)
    Start-Process -FilePath 'powershell.exe' -ArgumentList $watchArgs -WindowStyle Hidden
    Write-Log 'Started watcher process.'
    exit 0
}

if ($UninstallTask) {
    & schtasks.exe /Delete /F /TN $TaskName | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Could not remove scheduled task '$TaskName'" }
    Write-Log "Removed scheduled task '$TaskName'. Existing watcher processes must be stopped separately."
    exit 0
}

if ($Once) {
    Sync-Now
    exit 0
}

Sync-Now
$watcher = New-Object IO.FileSystemWatcher
$watcher.Path = $RepoRoot
$watcher.IncludeSubdirectories = $true
$watcher.NotifyFilter = [IO.NotifyFilters]'FileName, LastWrite, Size, DirectoryName'
$watcher.EnableRaisingEvents = $true
$pending = $false
$lastEvent = [DateTime]::MinValue

try {
    Write-Log "Watching $RepoRoot; debounce=${DebounceSeconds}s."
    while ($true) {
        $event = $watcher.WaitForChanged([IO.WatcherChangeTypes]::All, 1)
        if ($event.TimedOut) {
            if ($pending -and ((Get-Date) - $lastEvent).TotalSeconds -ge $DebounceSeconds) {
                $pending = $false
                Sync-Now
            }
            continue
        }
        $changed = Join-Path $RepoRoot $event.Name
        if (Test-ChangedPath $changed) {
            $pending = $true
            $lastEvent = Get-Date
        }
    }
} finally {
    $watcher.Dispose()
}
