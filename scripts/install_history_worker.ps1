param([string]$RuntimeRoot='D:\WaterbeRuntime', [string]$Python='C:\Program Files\Python312\pythonw.exe')
$ErrorActionPreference='Stop'
$sourceRoot=$PSScriptRoot
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python runtime missing' }
foreach($name in @('SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY')) {
    if (-not [Environment]::GetEnvironmentVariable($name,'User')) { throw 'Configure required user environment first' }
}
$releaseMaterial=(@('history_worker.py','operation_history.py','history_bootstrap.py') | ForEach-Object {(Get-FileHash -LiteralPath (Join-Path $sourceRoot $_)).Hash}) -join ''
$releaseBytes=[Text.Encoding]::UTF8.GetBytes($releaseMaterial)
$releaseId=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($releaseBytes)).Substring(0,16)
$releaseRoot=Join-Path $RuntimeRoot ('releases\'+$releaseId)
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
foreach($file in @('history_worker.py','operation_history.py','history_bootstrap.py')) {
    $target=Join-Path $releaseRoot $file
    if(Test-Path -LiteralPath $target) {
        if((Get-FileHash $target).Hash -ne (Get-FileHash (Join-Path $sourceRoot $file)).Hash) { throw 'Immutable release mismatch' }
    } else { Copy-Item -LiteralPath (Join-Path $sourceRoot $file) -Destination $target }
}
$notifyRoot=Join-Path $env:LOCALAPPDATA 'CAS-CL5200\logs'
$action=New-ScheduledTaskAction -Execute $Python -Argument ('"'+(Join-Path $releaseRoot 'history_bootstrap.py')+'" --database "'+(Join-Path $RuntimeRoot 'operations.db')+'" --source-root "'+(Split-Path $sourceRoot -Parent)+'" --notification-root "'+$notifyRoot+'" watch')
$trigger=New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$existing=Get-ScheduledTask -TaskName 'WaterbeOperationHistory' -ErrorAction SilentlyContinue
if($existing) {
    if(@($existing.Actions).Count -ne 1 -or $existing.Actions[0].Arguments -notlike '*history_bootstrap.py*') { throw 'Task ownership mismatch' }
    if($existing.State -eq 'Running') { Stop-ScheduledTask -TaskName 'WaterbeOperationHistory' }
}
Register-ScheduledTask -TaskName 'WaterbeOperationHistory' -Action $action -Trigger $trigger -Settings $settings -Description 'Read-only source observation and durable central history delivery; no scale writes' -Force | Out-Null
Start-ScheduledTask -TaskName 'WaterbeOperationHistory'
Get-ScheduledTask -TaskName 'WaterbeOperationHistory' | Select-Object TaskName,State
