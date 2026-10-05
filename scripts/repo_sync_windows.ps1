$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$mutex = [Threading.Mutex]::new($false, 'Local\WaterbeRepositorySync')
if (-not $mutex.WaitOne(0)) { exit 0 }
try {
    $statusJson = & python (Join-Path $PSScriptRoot 'repo_sync.py') --root $repositoryRoot
    $syncExit = $LASTEXITCODE
    $statusJson | & ssh -o BatchMode=yes -o ConnectTimeout=10 thinkpad '/usr/bin/python3 /home/sdg/waterbe/scripts/repo_sync.py --report-windows'
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Repository status requires review on ThinkPad' }
    exit $syncExit
}
finally { $mutex.ReleaseMutex(); $mutex.Dispose() }
