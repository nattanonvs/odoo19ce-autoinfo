<#
.SYNOPSIS
    STEP-STOP : หยุด Odoo 19 (+ Nginx) อย่างเป็นระเบียบ

.DESCRIPTION
    คู่ตรงข้ามของ STEP-3-Start-Odoo19.ps1 — ใช้หยุดสแตกที่ STEP-3 เริ่มไว้

    ขั้นตอน:
      [1/3] หยุด Odoo server (python odoo-bin) + process ที่จับพอร์ต Odoo
      [2/3] หยุด Nginx (port 80)
      [3/3] หยุด PostgreSQL service (เฉพาะเมื่อระบุ -StopPostgres)

    ค่าเริ่มต้นไม่แตะ PostgreSQL — ฐานข้อมูลยังเปิดให้บริการ/สำรองข้อมูลได้ตามปกติ
    (ใช้ -StopPostgres เมื่อต้องการหยุดทั้งสแตกจริง ๆ เช่นก่อนปิดเครื่อง)

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-STOP-Odoo19.ps1

.EXAMPLE
    # หยุดทั้งสแตก รวม PostgreSQL
    powershell -ExecutionPolicy Bypass -File .\STEP-STOP-Odoo19.ps1 -StopPostgres

.EXAMPLE
    # เรียกจากสคริปต์อื่น / Task Scheduler (ไม่ต้องรอกด Enter)
    powershell -ExecutionPolicy Bypass -File .\STEP-STOP-Odoo19.ps1 -NoPause
#>
param(
    [switch]$StopPostgres,
    [switch]$KeepNginx,
    [switch]$NoPause
)

$ErrorActionPreference = "Continue"   # ทำงานกับ service/process ภายนอก: จัดการ error แบบ explicit

# ===================== ค่าคงที่ของโปรเจกต์ =====================
$Root       = $PSScriptRoot
$Config     = Join-Path $Root "odoo.conf"
$PgService  = "postgresql-x64-16"                  # PostgreSQL service เดียวที่โปรเจกต์ใช้
$TotalSteps = 3

function Write-Step([int]$No, [string]$Text) {
    Write-Host "`n[$No/$TotalSteps] $Text" -ForegroundColor Yellow
}

function Read-OdooConf {
    $values = @{}
    if (Test-Path -LiteralPath $Config) {
        foreach ($line in Get-Content -LiteralPath $Config) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
                $values[$Matches[1]] = $Matches[2].Trim()
            }
        }
    }
    return $values
}

function Test-Port([int]$Port) {
    # ตรวจ listening socket ที่ "มี process จริงเป็นเจ้าของ" เท่านั้น
    # หลัง Stop-Process -Force Windows อาจทิ้ง ghost listener (OwningProcess = 0) ไว้ชั่วคราว
    # Get-NetTCPConnection -LocalPort อาจมองไม่เห็น listener บน [::] (dual-stack) จึง fallback netstat
    $real = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -and $_.OwningProcess -ne 0 }
    if ($real) { return $true }
    $hit = netstat -ano | Select-String -Pattern ":$Port\s" | Select-String -Pattern "LISTENING" |
           Where-Object { $_ -notmatch "LISTENING\s+0\s*$" }
    return [bool]$hit
}

function Stop-PortHolders([int[]]$Ports) {
    # ปิด process ที่ยังจับพอร์ตอยู่ — ตรวจ *ทุก* TCP state (ไม่ใช่แค่ Listen)
    # เพราะ process ที่ค้างตอนปิดตัวอาจเหลือ socket สถานะ FIN_WAIT_1/CLOSE_WAIT
    foreach ($port in $Ports | Select-Object -Unique) {
        $holders = @()
        # แหล่งที่ 1: Get-NetTCPConnection ทุก state
        $holders += Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
                    Select-Object -ExpandProperty OwningProcess -Unique
        # แหล่งที่ 2: netstat fallback — ครอบคลุม listener บน [::] (dual-stack) ที่อาจมองไม่เห็น
        $holders += netstat -ano | Select-String -Pattern ":$port\s" |
                    ForEach-Object { ($_.ToString().Trim() -split '\s+')[-1] }
        $holders | Where-Object { ($_ -as [int]) -and [int]$_ -gt 0 } | Sort-Object -Unique | ForEach-Object {
            Write-Host "  kill process on port $port (PID $_)" -ForegroundColor DarkYellow
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-PortFree([int[]]$Ports, [int]$MaxSeconds = 10) {
    foreach ($port in $Ports | Select-Object -Unique) {
        for ($i = 0; $i -lt $MaxSeconds; $i++) {
            if (-not (Test-Port $port)) { break }
            Start-Sleep -Seconds 1
        }
        if (Test-Port $port) {
            $left = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
                     Select-Object -ExpandProperty OwningProcess -Unique |
                     Where-Object { $_ -and $_ -ne 0 }) -join ', '
            if (-not $left) { $left = "(ตรวจ PID ไม่ได้)" }
            Write-Host "  เตือน: port $port ยังถูกจับอยู่ (PID $left)" -ForegroundColor Yellow
        }
    }
}

$conf       = Read-OdooConf
$httpPort   = 8070
$geventPort = 8072
if ($conf.ContainsKey('http_port')   -and $conf['http_port'])   { $httpPort   = [int]$conf['http_port'] }
if ($conf.ContainsKey('gevent_port') -and $conf['gevent_port']) { $geventPort = [int]$conf['gevent_port'] }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  STEP-STOP : หยุด Odoo 19" -ForegroundColor Cyan
Write-Host "  HTTP port : $httpPort  |  gevent : $geventPort" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$exitCode = 0

# ==========================================================================
# 1. หยุด Odoo server
# ==========================================================================
Write-Step 1 "หยุด Odoo server (python odoo-bin) และ process ที่จับพอร์ต Odoo"

# 1a. ปิด Odoo server (python odoo-bin) ทุกตัว — ตรวจจาก CommandLine เป็นหลัก
#     และ fallback ด้วย ExecutablePath ใต้ venv19 (บาง process อ่าน CommandLine ไม่ได้)
$venvDir = [regex]::Escape((Join-Path $Root "venv19"))
$odooProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq "python.exe" -and (
            ($_.CommandLine    -and $_.CommandLine    -match "odoo-bin") -or
            ($_.ExecutablePath -and $_.ExecutablePath -match $venvDir)
        )
    }
if ($odooProcs) {
    foreach ($proc in $odooProcs) {
        Write-Host "  kill Odoo process PID $($proc.ProcessId)" -ForegroundColor DarkYellow
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  ไม่พบ Odoo process ที่รันอยู่" -ForegroundColor Gray
}

# 1b. ปิด process ที่ยังจับพอร์ต Odoo อยู่ (8069 legacy / http_port / gevent_port)
Stop-PortHolders @(8069, $httpPort, $geventPort)

# 1c. รอจนพอร์ต Odoo ว่างจริง — ยืนยันผลการหยุด
Wait-PortFree @($httpPort, $geventPort)
if (Test-Port $httpPort) { $exitCode = 1 }

# ==========================================================================
# 2. หยุด Nginx
# ==========================================================================
Write-Step 2 "หยุด Nginx (port 80)"

if ($KeepNginx) {
    Write-Host "  ข้ามการหยุด Nginx (-KeepNginx)" -ForegroundColor Gray
} else {
    $nginxProcs = @(Get-Process nginx -ErrorAction SilentlyContinue)
    if ($nginxProcs.Count -gt 0) {
        foreach ($proc in $nginxProcs) {
            Write-Host "  kill nginx process PID $($proc.Id)" -ForegroundColor DarkYellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        # รอจน nginx หายทั้งหมดจริง (สูงสุด 10 วินาที) — worker สืบทอด listening socket จาก master
        for ($i = 0; $i -lt 10; $i++) {
            if (-not (Get-Process nginx -ErrorAction SilentlyContinue)) { break }
            Start-Sleep -Seconds 1
        }
        $nginxLeft = Get-Process nginx -ErrorAction SilentlyContinue
        if ($nginxLeft) {
            Write-Host "  เตือน: ยังมี nginx ค้างอยู่ (PID $(($nginxLeft.Id) -join ', '))" -ForegroundColor Yellow
            $exitCode = 1
        } else {
            Write-Host "  Nginx: Stopped" -ForegroundColor Green
        }
    } else {
        Write-Host "  ไม่พบ Nginx ที่รันอยู่" -ForegroundColor Gray
    }
}

# ==========================================================================
# 3. หยุด PostgreSQL (ทางเลือก)
# ==========================================================================
Write-Step 3 "หยุด PostgreSQL ($PgService)"

if ($StopPostgres) {
    $pg = Get-Service -Name $PgService -ErrorAction SilentlyContinue
    if (-not $pg) {
        Write-Host "  ไม่พบ service '$PgService' - ข้ามขั้นตอนนี้" -ForegroundColor Yellow
    } elseif ($pg.Status -eq "Stopped") {
        Write-Host "  PostgreSQL: Stopped อยู่แล้ว" -ForegroundColor Green
    } else {
        Write-Host "  กำลังหยุด PostgreSQL..." -ForegroundColor Yellow
        Stop-Service -Name $PgService -Force -ErrorAction SilentlyContinue
        for ($i = 0; $i -lt 10; $i++) {
            if ((Get-Service -Name $PgService).Status -eq "Stopped") { break }
            Start-Sleep -Seconds 1
        }
        if ((Get-Service -Name $PgService).Status -eq "Stopped") {
            Write-Host "  PostgreSQL: Stopped" -ForegroundColor Green
        } else {
            Write-Host "  PostgreSQL: หยุดไม่สำเร็จ" -ForegroundColor Red
            $exitCode = 1
        }
    }
} else {
    Write-Host "  ไม่หยุด PostgreSQL (ค่าเริ่มต้น) - ใช้ -StopPostgres ถ้าต้องการหยุดด้วย" -ForegroundColor Gray
}

# ==========================================================================
# สรุปผล
# ==========================================================================
Write-Host "`n========================================" -ForegroundColor Cyan
if ($exitCode -eq 0) { Write-Host "  STEP-STOP เสร็จสิ้นสมบูรณ์" -ForegroundColor Green }
else { Write-Host "  STEP-STOP เสร็จสิ้น แต่มีบางรายการยังค้างอยู่" -ForegroundColor Red }
Write-Host "========================================" -ForegroundColor Cyan

if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
exit $exitCode
