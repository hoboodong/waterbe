param(
    [ValidateSet('status','run','shell','upload','download')]
    [string]$Action = 'status',
    [string]$Command,
    [string]$LocalPath,
    [string]$RemotePath,
    [ValidateSet('waterbe','cascl5200','home')]
    [string]$Project = 'waterbe'
)
$ErrorActionPreference = 'Stop'
$remoteRoot = switch ($Project) {
    'waterbe' { '/home/sdg/waterbe' }
    'cascl5200' { '/home/sdg/cascl5200' }
    'home' { '/home/sdg' }
}
switch ($Action) {
    'status' {
        & ssh thinkpad 'hostname; date -Is; uptime; df -h /; systemctl is-active ssh tailscaled'
    }
    'run' {
        if (-not $Command) { throw 'Command is required.' }
        # A caller-supplied remote shell command; do not automatically retry mutations.
        & ssh thinkpad "cd '$remoteRoot' && $Command"
    }
    'shell' { & ssh -t thinkpad "cd '$remoteRoot' && exec bash -l" }
    'upload' {
        if (-not $LocalPath -or -not $RemotePath) { throw 'LocalPath and RemotePath are required.' }
        if ($RemotePath -notmatch '^/home/sdg/[A-Za-z0-9_./-]+$' -or $RemotePath -match '(^|/)\.\.(/|$)') { throw 'Use an explicit safe path under /home/sdg.' }
        $resolved = (Resolve-Path -LiteralPath $LocalPath).Path
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw 'Only single-file transfers are supported.' }
        & ssh thinkpad "test ! -e '$RemotePath'"
        if ($LASTEXITCODE -ne 0) { throw 'Destination exists or could not be checked; transfer cancelled.' }
        & scp $resolved "thinkpad:$RemotePath"
    }
    'download' {
        if (-not $LocalPath -or -not $RemotePath) { throw 'LocalPath and RemotePath are required.' }
        if ($RemotePath -notmatch '^/home/sdg/[A-Za-z0-9_./-]+$' -or $RemotePath -match '(^|/)\.\.(/|$)') { throw 'Use an explicit safe path under /home/sdg.' }
        if (Test-Path -LiteralPath $LocalPath) { throw 'Local destination exists; transfer cancelled.' }
        & scp "thinkpad:$RemotePath" $LocalPath
    }
}
if ($LASTEXITCODE -ne 0) { throw "ThinkPad operation failed (exit $LASTEXITCODE). No automatic retry was performed." }
