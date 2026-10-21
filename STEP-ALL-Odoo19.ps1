<#
.SYNOPSIS
    STEP-ALL : สั่งงานครบกระบวนการ Odoo 19 (git -> STEP-1 update -> STEP-2 install -> STEP-3 start)

.DESCRIPTION
    สคริปต์ตัวเดียวสำหรับสั่งงานทั้งกระบวนการ deploy บนเครื่องนี้:
      [0/3] git pull + submodule update (ข้ามได้ด้วย -NoGit)
      [1/3] STEP-1-Update-Odoo19.ps1      update โมดูลที่ติดตั้งแล้ว (dynamic จาก DB)
      [2/3] STEP-2-Install-Odoo19.ps1     ติดตั้งโมดูลใหม่ (เฉพาะเมื่อระบุ -Install หรือ -InstallAll)
      [3/3] STEP-3-Start-Odoo19.ps1       start Odoo + Nginx + DDNS

    ทุกขั้นตอนเรียกเป็น process แยก ถ้าขั้นใดล้มเหลวจะหยุดทันที (ไม่ไปต่อ)
    ไม่แตะ STEP-4 (backup) เพราะเป็นงานตามตารางเวลารายเดือน ไม่ใช่ส่วนของ start

    ข้อกำหนดของโปรเจกต์: ใช้ฐานข้อมูลเดียวคือ odoo19_pdev เท่านั้น

.EXAMPLE
    # ใช้งานปกติ: pull โค้ด -> update -> start
    powershell -ExecutionPolicy Bypass -File .\STEP-ALL-Odoo19.ps1

.EXAMPLE
    # มีโมดูลใหม่ต้องติดตั้งก่อน start
    powershell -ExecutionPolicy Bypass -File .\STEP-ALL-Odoo19.ps1 -Install od19_accounting_reporting,od19_inventory_reporting

.EXAMPLE
    # ติดตั้งทุกโมดูลใน custom_addons ที่ยังไม่ติดตั้ง แล้ว start
    powershell -ExecutionPolicy Bypass -File .\STEP-ALL-Odoo19.ps1 -InstallAll

.EXAMPLE
    # ใช้โค้ดบนเครื่องปัจจุบัน ไม่ต้อง git pull และ start อย่างเดียว
    powershell -ExecutionPolicy Bypass -File .\STEP-ALL-Odoo19.ps1 -NoGit -SkipUpdate
#>
param(
    [string]$Branch = "19.0",
    [string[]]$Install = @(),
    [switch]$InstallAll,
    [switch]$NoGit,
    [switch]$SkipUpdate,
    [switch]$SkipInstall,
    [switch]$SkipStart,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Step1 = Join-Path $Root "STEP-1-Update-Odoo19.ps1"
$Step2 = Join-Path $Root "STEP-2-Install-Odoo19.ps1"
$Step3 = Join-Path $Root "STEP-3-Start-Odoo19.ps1"

function Invoke-Git([string[]]$GitArgs) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & git -C $Root @GitArgs 2>&1 | ForEach-Object { Write-Host "  $_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) { throw "git $($GitArgs -join ' ') ล้มเหลว (exit $code)" }
}

function Invoke-StepScript([string]$Path, [string[]]$Arguments) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "ไม่พบสคริปต์: $Path" }
    Write-Host "`n=== เรียก $(Split-Path -Leaf $Path) ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Path @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$(Split-Path -Leaf $Path) ล้มเหลว (exit $LASTEXITCODE)" }
}

try {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  STEP-ALL : ครบกระบวนการ Odoo 19" -ForegroundColor Cyan
    Write-Host "  Database : odoo19_pdev" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # ---------- 0. git ----------
    if ($NoGit) {
        Write-Host "`n[0/3] ข้าม git pull (-NoGit)" -ForegroundColor Yellow
    } else {
        Write-Host "`n[0/3] git pull origin $Branch + submodule update" -ForegroundColor Yellow
        Invoke-Git @('pull', 'origin', $Branch)
        Invoke-Git @('submodule', 'update', '--init', '--recursive')
    }

    # ---------- 1. update โมดูลที่ติดตั้งแล้ว ----------
    if ($SkipUpdate) {
        Write-Host "`n[1/3] ข้าม STEP-1 update (-SkipUpdate)" -ForegroundColor Yellow
    } else {
        Write-Host "`n[1/3] STEP-1 : update โมดูลที่ติดตั้งแล้ว" -ForegroundColor Yellow
        Invoke-StepScript $Step1 @("-Branch", $Branch, "-NoGit", "-NoPause")
    }

    # ---------- 2. install โมดูลใหม่ ----------
    if ($SkipInstall) {
        Write-Host "`n[2/3] ข้าม STEP-2 install (-SkipInstall)" -ForegroundColor Yellow
    } elseif ($InstallAll) {
        Write-Host "`n[2/3] STEP-2 : ติดตั้งทุกโมดูลที่ยังไม่ติดตั้ง (-InstallAll)" -ForegroundColor Yellow
        Invoke-StepScript $Step2 @("-All", "-NoPause")
    } elseif ($Install.Count -gt 0) {
        Write-Host "`n[2/3] STEP-2 : ติดตั้งโมดูลที่ระบุ" -ForegroundColor Yellow
        Invoke-StepScript $Step2 @("-Modules", ($Install -join ","), "-NoPause")
    } else {
        Write-Host "`n[2/3] ข้าม STEP-2 (ไม่มีโมดูลใหม่ - ใช้ -Install หรือ -InstallAll ถ้าต้องติดตั้ง)" -ForegroundColor Gray
    }

    # ---------- 3. start ----------
    if ($SkipStart) {
        Write-Host "`n[3/3] ข้าม STEP-3 start (-SkipStart)" -ForegroundColor Yellow
    } else {
        Write-Host "`n[3/3] STEP-3 : start Odoo + Nginx + DDNS" -ForegroundColor Yellow
        Invoke-StepScript $Step3 @("-NoPause")
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  STEP-ALL เสร็จสิ้นสมบูรณ์" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
} catch {
    Write-Host "`n[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "หยุดกระบวนการ (ไม่ได้ไปขั้นตอนถัดไป)" -ForegroundColor Red
    if ($NoPause) { throw }
    exit 1
} finally {
    if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
}
