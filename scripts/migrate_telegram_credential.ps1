$ErrorActionPreference = 'Stop'
$telegramRoot = Join-Path $env:LOCALAPPDATA 'CAS-CL5200/telegram-failure-reporter'
$telegramConfig = Get-Content -LiteralPath (Join-Path $telegramRoot 'config.json') -Raw | ConvertFrom-Json
$protectedPath = Join-Path $telegramRoot ('token-' + $telegramConfig.credential_generation + '.dpapi')
Add-Type -AssemblyName System.Security
$protectedBytes = [IO.File]::ReadAllBytes($protectedPath)
$plainBytes = $null
try {
    $plainBytes = [Security.Cryptography.ProtectedData]::Unprotect($protectedBytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    $telegramToken = [Text.UTF8Encoding]::new($false, $true).GetString($plainBytes)
    if ($telegramToken -notmatch '^\d+:[A-Za-z0-9_-]+$') { throw 'Invalid Telegram token' }
    ('TELEGRAM_BOT_TOKEN=' + $telegramToken) | ssh thinkpad 'umask 077; test ! -e /home/sdg/.config/waterbe/telegram.env && install -m 600 /dev/stdin /home/sdg/.config/waterbe/telegram.env'
    if ($LASTEXITCODE -ne 0) { throw 'Protected credential transfer failed' }
    Write-Output 'Telegram credential transferred privately'
}
finally {
    if ($plainBytes) { [Array]::Clear($plainBytes, 0, $plainBytes.Length) }
    [Array]::Clear($protectedBytes, 0, $protectedBytes.Length)
    $telegramToken = $null
}
