# ============================================================
#  STEP-NETWORK : Odoo 19 Network Access Setup (Run as Administrator)
#  Domain: http://pdev-erp.auto-info.com
# ============================================================
#  ใช้ครั้งเดียวต่อเครื่อง (one-time setup): เปิด firewall port 80
#  และเพิ่ม entry ใน hosts file ของเครื่องนี้
#  ไม่ใช่สคริปต์ที่ต้องรันทุกครั้งที่ start Odoo
#
#  Usage:
#  1. Open PowerShell as Administrator
#  2. Run:
#     Set-ExecutionPolicy Bypass -Scope Process -Force
#     & "C:\odoo-dev\odoo19\STEP-NETWORK-Setup-Odoo19.ps1"
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Odoo 19 Network Access Setup" -ForegroundColor Cyan
Write-Host "  Domain: pdev-erp.auto-info.com" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Check Administrator privileges ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "        Right-click PowerShell -> Run as Administrator" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Running as Administrator" -ForegroundColor Green
Write-Host ""

# --- 1. Open Firewall Port 80 (HTTP) ---
Write-Host "[1/3] Configuring Windows Firewall (Port 80)..." -ForegroundColor Yellow

# Remove old rule if exists
$existingRule = Get-NetFirewallRule -DisplayName "Odoo19-Nginx-HTTP-80" -ErrorAction SilentlyContinue
if ($existingRule) {
    Remove-NetFirewallRule -DisplayName "Odoo19-Nginx-HTTP-80" -ErrorAction SilentlyContinue
    Write-Host "      Removed old rule" -ForegroundColor Gray
}

# Create new rule
New-NetFirewallRule -DisplayName "Odoo19-Nginx-HTTP-80" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 80 `
    -Action Allow `
    -Profile Any `
    -Description "Allow HTTP access to Odoo 19 via nginx reverse proxy" | Out-Null

Write-Host "      Port 80 opened successfully" -ForegroundColor Green
Write-Host ""

# --- 2. Add entry to hosts file ---
Write-Host "[2/3] Configuring hosts file (pdev-erp.auto-info.com)..." -ForegroundColor Yellow

$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$hostsContent = Get-Content $hostsPath -Raw

# Check if entry already exists
if ($hostsContent -match "pdev-erp\.auto-info\.com") {
    Write-Host "      Entry already exists, skipping" -ForegroundColor Gray
} else {
    $entry = "`n# Odoo 19 PDEV`n127.0.0.1 pdev-erp.auto-info.com`n"
    Add-Content -Path $hostsPath -Value $entry
    Write-Host "      Added: 127.0.0.1 pdev-erp.auto-info.com" -ForegroundColor Green
}
Write-Host ""

# --- 3. Verify connectivity ---
Write-Host "[3/3] Verifying connectivity..." -ForegroundColor Yellow

# Check if nginx is running
$nginxRunning = Get-Process -Name nginx -ErrorAction SilentlyContinue
if ($nginxRunning) {
    Write-Host "      nginx is running (PID: $($nginxRunning[0].Id))" -ForegroundColor Green
} else {
    Write-Host "      [WARN] nginx is NOT running!" -ForegroundColor Red
    Write-Host "      ใช้สคริปต์ STEP-3-Start-Odoo19.ps1 เพื่อ start nginx" -ForegroundColor Yellow
}

# Test access via domain
try {
    $response = Invoke-WebRequest -Uri "http://pdev-erp.auto-info.com/web" -UseBasicParsing -TimeoutSec 10
    Write-Host "      Access OK (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "      [WARN] Cannot access: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# --- Summary ---
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [OK] Firewall Port 80 opened" -ForegroundColor Green
Write-Host "  [OK] hosts file configured (this machine)" -ForegroundColor Green
Write-Host ""
Write-Host "  For other machines on the network:" -ForegroundColor Yellow
Write-Host "  -------------------------------------------"
Write-Host "  Option 1 (Recommended): Add DNS A Record" -ForegroundColor White
Write-Host "    On company DNS server, add:" -ForegroundColor White
Write-Host "    pdev-erp.auto-info.com  ->  IP of this machine" -ForegroundColor White
Write-Host "    (Current IP: 172.20.1.166 or 10.99.99.6)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option 2: Edit hosts file on each client" -ForegroundColor White
Write-Host "    Add this line to C:\Windows\System32\drivers\etc\hosts" -ForegroundColor White
Write-Host "    172.20.1.166 pdev-erp.auto-info.com" -ForegroundColor White
Write-Host "    (use the IP matching your network)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Access URL: http://pdev-erp.auto-info.com" -ForegroundColor Green
Write-Host ""
Write-Host "Setup complete. You can close this window." -ForegroundColor Cyan
