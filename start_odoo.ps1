# Odoo 19 Startup Script
# Run this after computer restart to start all services
# Usage: Right-click -> Run with PowerShell (or run in PowerShell)

$ErrorActionPreference = "Continue"
$odooPath = "C:\odoo-dev\odoo19"
$nginxPath = "C:\odoo-dev\odoo19\nginx\nginx-1.27.2"
$odooConf = "C:\odoo-dev\odoo19\odoo.conf"
$odooLog = "C:\odoo-dev\odoo19\odoo_server.log"
$ddnsScript = "C:\odoo-dev\odoo19\cloudflare_ddns.ps1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Odoo 19 Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check PostgreSQL
Write-Host "`n[1/4] Checking PostgreSQL..." -ForegroundColor Yellow
$pg = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
if ($pg.Status -eq "Running") {
    Write-Host "  PostgreSQL: Running" -ForegroundColor Green
} else {
    Write-Host "  Starting PostgreSQL..." -ForegroundColor Yellow
    Start-Service $pg -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    $pg = Get-Service -Name "postgresql-x64-16"
    if ($pg.Status -eq "Running") {
        Write-Host "  PostgreSQL: Started" -ForegroundColor Green
    } else {
        Write-Host "  PostgreSQL: FAILED to start" -ForegroundColor Red
    }
}

# 2. Start Odoo
Write-Host "`n[2/4] Starting Odoo (port 8070)..." -ForegroundColor Yellow
$odooRunning = Get-NetTCPConnection -LocalPort 8070 -State Listen -ErrorAction SilentlyContinue
if ($odooRunning) {
    Write-Host "  Odoo: Already running on port 8070" -ForegroundColor Green
} else {
    Write-Host "  Starting Odoo..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$odooPath'; python odoo-bin -c '$odooConf'" -WindowStyle Normal
    Write-Host "  Waiting for Odoo to start..." -ForegroundColor Yellow
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 2
        $elapsed += 2
        $check = Get-NetTCPConnection -LocalPort 8070 -State Listen -ErrorAction SilentlyContinue
        if ($check) {
            Write-Host "  Odoo: Started (port 8070) after $elapsed seconds" -ForegroundColor Green
            break
        }
    }
    if (-not $check) {
        Write-Host "  Odoo: May still be starting, check log: $odooLog" -ForegroundColor Yellow
    }
}

# 3. Start Nginx
Write-Host "`n[3/4] Starting Nginx (port 80)..." -ForegroundColor Yellow
$nginxRunning = Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue
if ($nginxRunning) {
    Write-Host "  Nginx: Already running on port 80" -ForegroundColor Green
} else {
    Write-Host "  Starting Nginx..." -ForegroundColor Yellow
    # Start nginx as a fully detached process (survives console close)
    $ret = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="`"$nginxPath\nginx.exe`""; CurrentDirectory=$nginxPath}
    Start-Sleep -Seconds 3
    $check = Get-NetTCPConnection -LocalPort 80 -State Listen -ErrorAction SilentlyContinue
    if ($check) {
        Write-Host "  Nginx: Started (port 80)" -ForegroundColor Green
    } else {
        Write-Host "  Nginx: FAILED to start" -ForegroundColor Red
    }
}

# 4. Update Cloudflare DNS (DDNS)
Write-Host "`n[4/4] Updating Cloudflare DNS (DDNS)..." -ForegroundColor Yellow
if (Test-Path $ddnsScript) {
    & powershell -ExecutionPolicy Bypass -File $ddnsScript
    Write-Host "  DDNS: Done (check log: C:\odoo-dev\odoo19\ddns_update.log)" -ForegroundColor Green
} else {
    Write-Host "  DDNS script not found: $ddnsScript" -ForegroundColor Yellow
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Startup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nAccess URLs:" -ForegroundColor Cyan
Write-Host "  Local:    http://localhost/web" -ForegroundColor White
Write-Host "  Network:  http://172.20.1.166/web" -ForegroundColor White
Write-Host "  Internet: https://pdev-erp.auto-info.com" -ForegroundColor White
Write-Host "`nOdoo log: $odooLog" -ForegroundColor Gray
Write-Host "DDNS log: C:\odoo-dev\odoo19\ddns_update.log" -ForegroundColor Gray
Write-Host "`nPress Enter to close..." -ForegroundColor Gray
Read-Host
