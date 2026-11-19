<#
.SYNOPSIS
    STEP-RESTART : รีสตาร์ท Odoo 19 (หยุด -> เริ่มใหม่)

.DESCRIPTION
    ตัวห่อที่เรียกตามลำดับ:
      [1/2] STEP-STOP-Odoo19.ps1     หยุด Odoo + Nginx
      [2/2] STEP-3-Start-Odoo19.ps1  เริ่ม Odoo + Nginx + DDNS

    ใช้หลังแก้ไขโค้ด Python / ไฟล์ config (Odoo ต้องรีสตาร์ทให้การเปลี่ยนแปลงมีผล)
    ถ้าขั้นตอนใดล้มเหลวจะหยุดทันที (ไม่ไปต่อ) และรายงาน exit code

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-RESTART-Odoo19.ps1

.EXAMPLE
    # รีสตาร์ททั้งสแตก รวม PostgreSQL
    powershell -ExecutionPolicy Bypass -File .\STEP-RESTART-Odoo19.ps1 -StopPostgres

.EXAMPLE
    # เรียกจากสคริปต์อื่น / Task Scheduler (ไม่ต้องรอกด Enter)
    powershell -ExecutionPolicy Bypass -File .\STEP-RESTART-Odoo19.ps1 -NoPause
#>
param(
    [switch]$StopPostgres,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$Root  = $PSScriptRoot
$Stop  = Join-Path $Root "STEP-STOP-Odoo19.ps1"
$Start = Join-Path $Root "STEP-3-Start-Odoo19.ps1"

function Invoke-StepScript([string]$Path, [string[]]$Arguments) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "ไม่พบสคริปต์: $Path" }
    Write-Host "`n=== เรียก $(Split-Path -Leaf $Path) ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Path @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$(Split-Path -Leaf $Path) ล้มเหลว (exit $LASTEXITCODE)" }
}

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  STEP-RESTART : รีสตาร์ท Odoo 19" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # ---------- 1. หยุด ----------
    Write-Host "`n[1/2] STEP-STOP : หยุด Odoo + Nginx" -ForegroundColor Yellow
    $stopArgs = @("-NoPause")
    if ($StopPostgres) { $stopArgs += "-StopPostgres" }
    Invoke-StepScript $Stop $stopArgs

    # รอให้ process/พอร์ตเคลียร์ก่อนเริ่มใหม่
    Start-Sleep -Seconds 2

    # ---------- 2. เริ่ม ----------
    Write-Host "`n[2/2] STEP-3 : เริ่ม Odoo + Nginx + DDNS" -ForegroundColor Yellow
    Invoke-StepScript $Start @("-NoPause")

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  STEP-RESTART เสร็จสิ้นสมบูรณ์" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
} catch {
    Write-Host "`n[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "หยุดกระบวนการ (ไม่ได้ไปขั้นตอนถัดไป)" -ForegroundColor Red
    if ($NoPause) { throw }
    exit 1
} finally {
    if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
}
