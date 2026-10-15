# Odoo 19 - monthly backup wrapper (Windows Task Scheduler entry point).
# Calls backup_odoo19.py with the project virtualenv and appends output to logs\backup_<yyyy-MM>.log
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root 'venv19\Scripts\python.exe'
$Script = Join-Path $Root 'backup_odoo19.py'
$LogDir = Join-Path $Root 'logs'
$Log = Join-Path $LogDir ('backup_' + (Get-Date -Format 'yyyy-MM') + '.log')

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Make pg_dump available: odoo.tools.misc.find_pg_tool looks it up in PATH.
$PgRoot = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if ($PgRoot) {
    $PgBin = Join-Path $PgRoot.FullName 'bin'
    if (Test-Path (Join-Path $PgBin 'pg_dump.exe')) { $env:PATH = "$PgBin;$env:PATH" }
}

$env:PYTHONPATH = "$Root;$env:PYTHONPATH"

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -Path $Log -Value "[$stamp] ==== backup start ===="

& $Python $Script *>&1 | Tee-Object -FilePath $Log -Append
$code = $LASTEXITCODE

Add-Content -Path $Log -Value ("[{0}] ==== backup end (exit {1}) ====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $code)
exit $code
