<#
.SYNOPSIS
    STEP-5 : ตรวจสอบไฟล์สำรอง Odoo 19 ด้วยการกู้คืนจริง (weekly restore drill)

.DESCRIPTION
    ตัวห่อสำหรับ Windows Task Scheduler (งานรายสัปดาห์)
    เรียก STEP-5-Verify-Backup-Odoo19.py ด้วย virtualenv ของโปรเจกต์
    แล้วต่อท้าย log ลง logs\backup-verify_<yyyy-MM>.log

    ตรวจว่าไฟล์สำรองล่าสุดกู้คืนได้จริง โดย
      - เทียบ size + sha256 กับ backups\backup-manifest.jsonl
      - กู้คืนลงฐานข้อมูลชั่วคราว (ค่าเริ่มต้น odoo19_restoretest)
      - ตรวจตารางหลัก แล้วลบฐานข้อมูลชั่วคราวทิ้ง
    คืนค่า exit 0 = ผ่าน, 1 = ไม่ผ่าน

    ต้องให้ pg tools (psql / pg_restore) อยู่ใน PATH เพื่อให้ restore_db ทำงานได้
    (สคริปต์นี้เติม PATH ให้อัตโนมัติจาก C:\Program Files\PostgreSQL)

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-5-Verify-Backup-Odoo19.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-5-Verify-Backup-Odoo19.ps1 -Database odoo19_pdev -TempDatabase odoo19_restoretest
#>
param(
    [string]$Database = "odoo19_pdev",
    [string]$TempDatabase = "odoo19_restoretest"
)

$ErrorActionPreference = 'Stop'

$Root   = $PSScriptRoot
$Python = Join-Path $Root 'venv19\Scripts\python.exe'
$Script = Join-Path $Root 'STEP-5-Verify-Backup-Odoo19.py'
$Config = Join-Path $Root 'odoo.conf'
$LogDir = Join-Path $Root 'logs'
$Log    = Join-Path $LogDir ('backup-verify_' + (Get-Date -Format 'yyyy-MM') + '.log')

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# ทำให้ psql / pg_restore หาเจอ: odoo.tools.misc.find_pg_tool ค้นหาจาก PATH
$PgRoot = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if ($PgRoot) {
    $PgBin = Join-Path $PgRoot.FullName 'bin'
    if (Test-Path (Join-Path $PgBin 'psql.exe')) { $env:PATH = "$PgBin;$env:PATH" }
}

$env:PYTHONPATH = "$Root;$env:PYTHONPATH"

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -Path $Log -Value "[$stamp] ==== verify start (db: $Database -> $TempDatabase) ===="

& $Python $Script --conf $Config --db $Database --temp-db $TempDatabase *>&1 | Tee-Object -FilePath $Log -Append
$code = $LASTEXITCODE

Add-Content -Path $Log -Value ("[{0}] ==== verify end (exit {1}) ====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $code)
exit $code
