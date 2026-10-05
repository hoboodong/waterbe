param([string]$LogRoot="$env:LOCALAPPDATA/CAS-CL5200/logs")
$ErrorActionPreference='Stop'
# Temporary bridge until the Telegram reporter itself is migrated.
$remoteFiles = & ssh -o BatchMode=yes -o ConnectTimeout=10 thinkpad 'find /home/sdg/.local/state/waterbe-central/logs -maxdepth 1 -type f -name "worker-history-*.jsonl" -printf "%f\n"'
if ($LASTEXITCODE -ne 0) { throw 'ThinkPad history log access failed.' }
foreach ($remoteFile in $remoteFiles) {
    if ($remoteFile -notmatch '^worker-history-[0-9]{8}\.jsonl$') { throw 'Unexpected remote log name.' }
    $temporaryFile = [IO.Path]::GetTempFileName()
    try {
        & scp -q "thinkpad:/home/sdg/.local/state/waterbe-central/logs/$remoteFile" $temporaryFile
        if ($LASTEXITCODE -ne 0) { throw 'Log transfer failed.' }
        foreach ($line in [IO.File]::ReadAllLines($temporaryFile)) {
            if ($line.Trim()) {
                $entry = $line | ConvertFrom-Json
                if ($entry.event -ne 'waterbe_history_health') { throw 'Unexpected event type.' }
            }
        }
        $destination = Join-Path $LogRoot ($remoteFile.Replace('worker-history-','worker-thinkpad-history-'))
        Move-Item -LiteralPath $temporaryFile -Destination $destination -Force
    } finally {
        if (Test-Path -LiteralPath $temporaryFile) { Remove-Item -LiteralPath $temporaryFile }
    }
}
