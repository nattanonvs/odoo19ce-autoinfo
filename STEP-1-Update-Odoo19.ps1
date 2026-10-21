<#
.SYNOPSIS
    STEP-1 : Update โมดูล Odoo 19 (ฐานข้อมูล odoo19_pdev)

.DESCRIPTION
    หารายชื่อโมดูลที่จะ update แบบ dynamic จากข้อมูลจริง ไม่ต้องแก้รายชื่อในไฟล์:
      1. query ฐานข้อมูล odoo19_pdev เอาโมดูลที่ state = 'installed'
      2. ตัดเอาเฉพาะโมดูลที่มีโฟลเดอร์อยู่ใน custom_addons (โมดูลที่โปรเจกต์พัฒนเอง)
      3. สั่ง update แบบ batch เดียว: odoo-bin -u <list> --stop-after-init

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-1-Update-Odoo19.ps1

.EXAMPLE
    # ข้าม git pull (update จากโค้ดบนเครื่องปัจจุบัน)
    powershell -ExecutionPolicy Bypass -File .\STEP-1-Update-Odoo19.ps1 -NoGit
#>
param(
    [string]$Branch = "19.0",
    [switch]$NoGit,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

# ===================== ค่าคงที่ของโปรเจกต์ =====================
$Root         = $PSScriptRoot
$Database     = "odoo19_pdev"                        # ฐานข้อมูลเดียวที่อนุญาตให้ใช้
$Python       = Join-Path $Root "venv19\Scripts\python.exe"
$OdooBin      = Join-Path $Root "odoo-bin"
$Config       = Join-Path $Root "odoo.conf"
$CustomAddons = Join-Path $Root "custom_addons"
$TotalSteps   = 3

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

function Get-PsqlPath {
    $pgRoot = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $pgRoot) { return $null }
    $exe = Join-Path $pgRoot.FullName 'bin\psql.exe'
    if (Test-Path -LiteralPath $exe) { return $exe }
    return $null
}

function Get-InstalledModules([string]$Psql, [string]$User, [string]$Password) {
    $env:PGPASSWORD = $Password
    try {
        $rows = & $Psql -U $User -h localhost -d $Database -t -A -c "SELECT name FROM ir_module_module WHERE state = 'installed' ORDER BY name"
        $code = $LASTEXITCODE
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
    if ($code -ne 0) { throw "query ir_module_module ล้มเหลว (exit $code)" }
    return @($rows | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Get-CustomModules {
    return @(Get-ChildItem -LiteralPath $CustomAddons -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName '__manifest__.py') } |
        Select-Object -ExpandProperty Name)
}

function Assert-OdooStopped([int]$HttpPort) {
    if (Get-NetTCPConnection -LocalPort $HttpPort -State Listen -ErrorAction SilentlyContinue) {
        throw "Odoo กำลังรันอยู่ที่ port $HttpPort - กรุณาหยุด Odoo ก่อน แล้วรัน STEP-1 อีกครั้ง"
    }
}

function Invoke-Git([string[]]$GitArgs) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & git -C $Root @GitArgs 2>&1 | ForEach-Object { Write-Host "  $_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { throw "git $($GitArgs -join ' ') ล้มเหลว (exit $code)" }
}

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  STEP-1 : Update โมดูล Odoo 19" -ForegroundColor Cyan
    Write-Host "  Database : $Database" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    foreach ($path in @($Python, $OdooBin, $Config, $CustomAddons)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "ไม่พบไฟล์/โฟลเดอร์ที่จำเป็น: $path" }
    }

    # ---------- 1. หาโมดูลที่จะ update จากฐานข้อมูลจริง ----------
    Write-Step 1 "ตรวจรายชื่อโมดูลจากฐานข้อมูล $Database ..."

    $psql = Get-PsqlPath
    if (-not $psql) { throw "ไม่พบ psql.exe - ตรวจสอบการติดตั้ง PostgreSQL" }

    $conf   = Read-OdooConf
    $dbUser = 'odoo'
    $dbPass = ''
    if ($conf.ContainsKey('db_user'))     { $dbUser = $conf['db_user'] }
    if ($conf.ContainsKey('db_password')) { $dbPass = $conf['db_password'] }

    Assert-OdooStopped ([int]($(if ($conf.ContainsKey('http_port')) { $conf['http_port'] } else { 8070 })))

    $installed     = Get-InstalledModules -Psql $psql -User $dbUser -Password $dbPass
    $customModules = Get-CustomModules
    $toUpdate      = @($customModules | Where-Object { $installed -contains $_ } | Sort-Object)
    $notInstalled  = @($customModules | Where-Object { $installed -notcontains $_ } | Sort-Object)

    Write-Host "  โมดูลใน custom_addons      : $($customModules.Count)"
    Write-Host "  ติดตั้งแล้ว (จะ update)     : $($toUpdate.Count)" -ForegroundColor Green
    Write-Host "  ยังไม่ติดตั้ง (ใช้ STEP-2)  : $($notInstalled.Count)" -ForegroundColor DarkYellow
    if ($notInstalled.Count -gt 0) {
        Write-Host "    $($notInstalled -join ', ')" -ForegroundColor DarkGray
    }
    if ($toUpdate.Count -eq 0) { throw "ไม่พบโมดูลที่ต้อง update ในฐานข้อมูล $Database" }
    $toUpdate | ForEach-Object { Write-Host "    - $_" -ForegroundColor Gray }

    # ---------- 2. git (ถ้าไม่สั่งข้าม) ----------
    if ($NoGit) {
        Write-Step 2 "ข้าม git pull (-NoGit)"
    } else {
        Write-Step 2 "git pull origin $Branch + submodule update"
        Invoke-Git @('pull', 'origin', $Branch)
        Invoke-Git @('submodule', 'update', '--init', '--recursive')
    }

    # ---------- 3. update ----------
    Write-Step 3 "update $($toUpdate.Count) โมดูล (--stop-after-init)"
    $list = $toUpdate -join ","
    & $Python $OdooBin -c $Config -d $Database -u $list --stop-after-init
    if ($LASTEXITCODE -ne 0) { throw "update ล้มเหลว (exit $LASTEXITCODE)" }

    Write-Host "`nSTEP-1 เสร็จสิ้นสมบูรณ์ (Database: $Database)" -ForegroundColor Green
} catch {
    Write-Host "`n[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if ($NoPause) { throw }
    exit 1
} finally {
    if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
}
