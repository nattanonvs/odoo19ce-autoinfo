<#
.SYNOPSIS
    STEP-4 : Backup ฐานข้อมูล Odoo 19 (ค่าเริ่มต้น odoo19_pdev)

.DESCRIPTION
    ตัวห่อสำหรับ Windows Task Scheduler (งานรายเดือน วันที่ 1 เวลา 03:00)
    เรียก STEP-4-Backup-Odoo19.py ด้วย virtualenv ของโปรเจกต์
    แล้วต่อท้าย log ลง logs\backup_<yyyy-MM>.log

    เพราะ odoo.conf ตั้ง list_db = False ทำให้ OCA auto_backup ที่ทำงานเป็น cron
    ภายในเซิร์ฟเวอร์จะโดน AccessDenied เสมอ จึงต้องรัน backup นอกเซิร์ฟเวอร์แบบนี้

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-4-Backup-Odoo19.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-4-Backup-Odoo19.ps1 -Database odoo19_pdev
#>
param(
    [string]$Database = "odoo19_pdev"
)

$ErrorActionPreference = 'Stop'

$Root   = $PSScriptRoot
$Python = Join-Path $Root 'venv19\Scripts\python.exe'
$Script = Join-Path $Root 'STEP-4-Backup-Odoo19.py'
$Config = Join-Path $Root 'odoo.conf'
$LogDir = Join-Path $Root 'logs'
$Log    = Join-Path $LogDir ('backup_' + (Get-Date -Format 'yyyy-MM') + '.log')

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# ทำให้ pg_dump หาเจอ: odoo.tools.misc.find_pg_tool ค้นหาจาก PATH
$PgRoot = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if ($PgRoot) {
    $PgBin = Join-Path $PgRoot.FullName 'bin'
    if (Test-Path (Join-Path $PgBin 'pg_dump.exe')) { $env:PATH = "$PgBin;$env:PATH" }
}

$env:PYTHONPATH = "$Root;$env:PYTHONPATH"

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -Path $Log -Value "[$stamp] ==== backup start (db: $Database) ===="

& $Python $Script --conf $Config --db $Database *>&1 | Tee-Object -FilePath $Log -Append
$code = $LASTEXITCODE

Add-Content -Path $Log -Value ("[{0}] ==== backup end (exit {1}) ====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $code)
exit $code
