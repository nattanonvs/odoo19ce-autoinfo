<#
.SYNOPSIS
    STEP-2 : ติดตั้งโมดูล Odoo 19 เท่านั้น (install-only, ฐานข้อมูล odoo19_pdev)

.DESCRIPTION
    ต่างจาก STEP-1 (update) ตรงที่สคริปต์นี้สั่ง -i เท่านั้น ไม่สั่ง -u
    และไม่ทำ git pull

    โมดูลที่ติดตั้งได้ต้องมีโฟลเดอร์อยู่ใน custom_addons แล้ว (merge เข้า branch ก่อน)

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    # ระบุโมดูลที่ต้องการติดตั้ง
    powershell -ExecutionPolicy Bypass -File .\STEP-2-Install-Odoo19.ps1 -Modules od19_accounting_reporting,od19_inventory_reporting

.EXAMPLE
    # ติดตั้งทุกโมดูลใน custom_addons ที่ยังไม่ติดตั้ง
    powershell -ExecutionPolicy Bypass -File .\STEP-2-Install-Odoo19.ps1 -All

.EXAMPLE
    # ดูรายชื่อโมดูลที่ติดตั้งได้ (ไม่ติดตั้งจริง)
    powershell -ExecutionPolicy Bypass -File .\STEP-2-Install-Odoo19.ps1 -WhatIfList
#>
param(
    [string[]]$Modules = @(),
    [switch]$All,
    [switch]$WhatIfList,
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
        throw "Odoo กำลังรันอยู่ที่ port $HttpPort - กรุณาหยุด Odoo ก่อน แล้วรัน STEP-2 อีกครั้ง"
    }
}

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  STEP-2 : ติดตั้งโมดูล Odoo 19" -ForegroundColor Cyan
    Write-Host "  Database : $Database" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    foreach ($path in @($Python, $OdooBin, $Config, $CustomAddons)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "ไม่พบไฟล์/โฟลเดอร์ที่จำเป็น: $path" }
    }

    $psql = Get-PsqlPath
    if (-not $psql) { throw "ไม่พบ psql.exe - ตรวจสอบการติดตั้ง PostgreSQL" }

    $conf   = Read-OdooConf
    $dbUser = 'odoo'
    $dbPass = ''
    if ($conf.ContainsKey('db_user'))     { $dbUser = $conf['db_user'] }
    if ($conf.ContainsKey('db_password')) { $dbPass = $conf['db_password'] }

    $installed     = Get-InstalledModules -Psql $psql -User $dbUser -Password $dbPass
    $customModules = Get-CustomModules
    $notInstalled  = @($customModules | Where-Object { $installed -notcontains $_ } | Sort-Object)

    Write-Host "`n  โมดูลใน custom_addons     : $($customModules.Count)"
    Write-Host "  ติดตั้งแล้ว                : $($customModules.Count - $notInstalled.Count)" -ForegroundColor Gray
    Write-Host "  ยังไม่ติดตั้ง (ติดตั้งได้) : $($notInstalled.Count)" -ForegroundColor Green
    if ($notInstalled.Count -gt 0) {
        Write-Host "    $($notInstalled -join ', ')" -ForegroundColor DarkGray
    }

    # ---------- หาเป้าหมายที่ต้องติดตั้ง ----------
    $targets = @()

    if ($All) {
        $targets = $notInstalled
    } elseif ($Modules.Count -gt 0) {
        foreach ($m in $Modules) {
            $name = $m.Trim()
            if (-not $name) { continue }
            if ($customModules -notcontains $name) {
                throw "ไม่พบโมดูล '$name' ใน custom_addons - ต้อง merge โมดูลเข้า branch ก่อนติดตั้ง"
            }
            if ($installed -contains $name) {
                Write-Host "  ข้าม '$name' (ติดตั้งอยู่แล้ว - ใช้ STEP-1 เพื่อ update)" -ForegroundColor DarkYellow
                continue
            }
            $targets += $name
        }
    } else {
        Write-Host "`nยังไม่ได้ระบุโมดูล ใช้หนึ่งในนี้:" -ForegroundColor Yellow
        Write-Host "  -Modules <ชื่อโมดูล คั่นด้วย ,>   ติดตั้งเฉพาะที่ระบุ"
        Write-Host "  -All                              ติดตั้งทุกโมดูลที่ยังไม่ติดตั้ง"
        Write-Host "  -WhatIfList                       ดูรายชื่อโดยไม่ติดตั้งจริง"
        if ($NoPause) { throw "ไม่ได้ระบุโมดูล (ใช้ -Modules หรือ -All)" }
        return
    }

    $targets = @($targets | Select-Object -Unique | Sort-Object)

    if ($WhatIfList) {
        Write-Host "`n[WhatIfList] โมดูลที่จะติดตั้ง ($($targets.Count)):" -ForegroundColor Cyan
        if ($targets.Count -eq 0) { Write-Host "  - ไม่มี -" -ForegroundColor Gray }
        $targets | ForEach-Object { Write-Host "    - $_" -ForegroundColor Gray }
        if ($NoPause) { return }
        return
    }

    if ($targets.Count -eq 0) {
        Write-Host "`nไม่มีโมดูลที่ต้องติดตั้ง - ไม่มีอะไรต้องทำ" -ForegroundColor Green
        return
    }

    Assert-OdooStopped ([int]($(if ($conf.ContainsKey('http_port')) { $conf['http_port'] } else { 8070 })))

    # ---------- ติดตั้ง ----------
    Write-Host "`n=== ติดตั้ง $($targets.Count) โมดูล (--stop-after-init) ===" -ForegroundColor Cyan
    $targets | ForEach-Object { Write-Host "    - $_" -ForegroundColor Gray }

    $list = $targets -join ","
    & $Python $OdooBin -c $Config -d $Database -i $list --stop-after-init
    if ($LASTEXITCODE -ne 0) { throw "ติดตั้งล้มเหลว (exit $LASTEXITCODE)" }

    # ---------- ตรวจผลหลังติดตั้ง ----------
    $installedAfter = Get-InstalledModules -Psql $psql -User $dbUser -Password $dbPass
    $failed = @($targets | Where-Object { $installedAfter -notcontains $_ })
    if ($failed.Count -gt 0) {
        throw "โมดูลต่อไปนี้ยังไม่ถูกติดตั้ง: $($failed -join ', ') - ดูรายละเอียดใน $Root\odoo_server.log"
    }

    Write-Host "`nSTEP-2 เสร็จสิ้นสมบูรณ์ - ติดตั้งสำเร็จ $($targets.Count) โมดูล" -ForegroundColor Green
} catch {
    Write-Host "`n[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if ($NoPause) { throw }
    exit 1
} finally {
    if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
}
