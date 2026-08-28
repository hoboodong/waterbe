param(
    [string]$WaitForPid = '',
    [int]$MaxParallel = 4
)

$ErrorActionPreference = 'Stop'
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = 'True'
$env:FLAGS_use_mkldnn = '0'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo

$results = 'tmp/daeyoung_all_results'
$logs = 'tmp/daeyoung_logs'
New-Item -ItemType Directory -Force $results, $logs | Out-Null

foreach ($processId in @($WaitForPid -split ',' | Where-Object { $_ })) {
    Wait-Process -Id $processId -ErrorAction SilentlyContinue
}

$queue = @(
    @{ Month='2026-02'; Input='tmp/daeyoung_history/2026-02'; Manifest='tmp/daeyoung_history_http_manifest.json'; Year='2026' },
    @{ Month='2026-03'; Input='tmp/daeyoung_history/2026-03'; Manifest='tmp/daeyoung_history_http_manifest.json'; Year='2026' },
    @{ Month='2026-04'; Input='tmp/daeyoung_history/2026-04'; Manifest='tmp/daeyoung_history_http_manifest.json'; Year='2026' },
    @{ Month='2026-05'; Input='tmp/daeyoung_history/2026-05'; Manifest='tmp/daeyoung_history_http_manifest.json'; Year='2026' },
    @{ Month='2026-06'; Input='tmp/daeyoung_history/2026-06'; Manifest='tmp/daeyoung_history_http_manifest.json'; Year='2026' },
    @{ Month='2026-07'; Input='tmp/daeyoung_2026_07'; Manifest='tmp/daeyoung_2026_07_http_manifest.json'; Year='2026' },
    @{ Month='2026-08'; Input='tmp/daeyoung_2026_08'; Manifest='tmp/daeyoung_2026_08_http_manifest.json'; Year='2026' }
)

$running = @{}
while ($queue.Count -gt 0 -or $running.Count -gt 0) {
    foreach ($month in @($running.Keys)) {
        $process = Get-Process -Id $running[$month].Id -ErrorAction SilentlyContinue
        if (-not $process) {
            if (-not (Test-Path "$results/${month}_report.json")) {
                throw "OCR failed for $month"
            }
            Write-Output "completed $month"
            $running.Remove($month)
        }
    }

    while ($queue.Count -gt 0 -and $running.Count -lt $MaxParallel) {
        $job = $queue[0]
        $queue = @($queue | Select-Object -Skip 1)
        if (Test-Path "$results/$($job.Month)_report.json") {
            Write-Output "skipped $($job.Month)"
            continue
        }
        $arguments = @(
            'scripts/daeyoung_sales_ocr.py', $job.Input,
            '--manifest', $job.Manifest,
            '--year', $job.Year,
            '--csv', "$results/$($job.Month)_sales.csv",
            '--report', "$results/$($job.Month)_report.json"
        )
        $process = Start-Process python -ArgumentList $arguments `
            -RedirectStandardOutput "$logs/$($job.Month).out.log" `
            -RedirectStandardError "$logs/$($job.Month).err.log" `
            -WindowStyle Hidden -PassThru
        $running[$job.Month] = $process
        Write-Output "started $($job.Month) pid=$($process.Id)"
    }
    if ($queue.Count -gt 0 -or $running.Count -gt 0) {
        Start-Sleep -Seconds 10
    }
}

python scripts/daeyoung_supabase_sync.py --results-root $results
if ($LASTEXITCODE -ne 0) {
    throw "Supabase sync failed with exit $LASTEXITCODE"
}
Write-Output 'ALL_COMPLETE'
