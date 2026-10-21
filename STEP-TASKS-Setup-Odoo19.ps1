<#
.SYNOPSIS
    STEP-TASKS : ลงทะเบียน Windows Scheduled Tasks ของ Odoo 19 (Run as Administrator, one-time)

.DESCRIPTION
    สคริปต์นี้ตั้งค่าตารางงานอัตโนมัติ 3 งาน ให้ชี้ไปที่สคริปต์ชุด STEP-* อย่างถูกต้อง
    และตั้งค่าให้งาน backup ทำงานได้แม้ไม่มีใครล็อกอินอยู่ (เดิมตั้งเป็น Interactive only
    ทำให้งานตี 3 ของวันที่ 1 ไม่รันเมื่อไม่มี session)

      [1/3] Odoo19 Auto Start        : At log on ของผู้ใช้ปัจจุบัน -> STEP-3 (RunLevel Highest)
      [2/3] Odoo19 Monthly Backup    : วันที่ 1 ของทุกเดือน 03:00 -> STEP-4, logon type S4U
      [3/3] Cloudflare DDNS - Odoo19 : ทุก 5 นาที -> STEP-DDNS

    ใช้ -TriggerTime ของงาน backup ตามต้องการ (ค่าเริ่มต้น 03:00)
    งานที่มีอยู่แล้วจะถูกปรับเฉพาะ action / principal / settings โดยไม่แตะ trigger เดิม
    ยกเว้นงานที่ยังไม่มี จึงจะสร้างใหม่พร้อม trigger

    หมายเหตุ S4U: "Run whether user is logged on or not" แบบไม่ต้องเก็บรหัสผ่าน Windows
    ข้อจำกัด: งานแบบ S4U เข้าถึง network share ด้วยสิทธิ์ผู้ใช้ไม่ได้
    (ถ้า db.backup ใน Odoo ตั้ง folder เป็น UNC path ให้กลับไปใช้ logon type Password)

.EXAMPLE
    # เปิด PowerShell as Administrator แล้วรัน
    powershell -ExecutionPolicy Bypass -File .\STEP-TASKS-Setup-Odoo19.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\STEP-TASKS-Setup-Odoo19.ps1 -TriggerTime 02:30

.EXAMPLE
    # ลบ task ทั้ง 3 ตัวออก
    powershell -ExecutionPolicy Bypass -File .\STEP-TASKS-Setup-Odoo19.ps1 -RemoveTasks
#>
param(
    [string]$TriggerTime = "03:00",
    [switch]$RemoveTasks,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$Root       = $PSScriptRoot
$TaskStart  = "Odoo19 Auto Start"
$TaskBackup = "Odoo19 Monthly Backup"
$TaskDdns   = "Cloudflare DDNS - Odoo19"
$User       = "$env:USERDOMAIN\$env:USERNAME"

$Step3 = Join-Path $Root "STEP-3-Start-Odoo19.ps1"
$Step4 = Join-Path $Root "STEP-4-Backup-Odoo19.ps1"
$Ddns  = Join-Path $Root "STEP-DDNS-Cloudflare-Odoo19.ps1"

$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

function Write-Head([string]$Text) {
    Write-Host "`n$Text" -ForegroundColor Yellow
}

function New-OdooTaskAction([string]$ScriptPath, [string]$ExtraArgs) {
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    if ($ExtraArgs) { $arg = "$arg $ExtraArgs" }
    return (New-ScheduledTaskAction -Execute $PowerShellExe -Argument $arg -WorkingDirectory $Root)
}

function New-OdooTaskSettings {
    return (New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 4))
}

# สร้าง Task XML สำหรับงานรายเดือน (วันที่ 1 ของทุกเดือน) แบบ logon type S4U
# จำเป็นเพราะ New-ScheduledTaskTrigger ไม่รองรับ monthly และ CIM (MSFT_TaskMonthlyTrigger)
# ตั้งค่า DaysOfMonth/MonthOfYear ไม่ได้บน Windows build นี้
function New-OdooMonthlyTaskXml {
    param(
        [string]$UserId, [string]$Time, [string]$Argument, [string]$Description
    )
    $parts = $Time.Split(':')
    $sb = (Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0).ToString("yyyy-MM-dd'T'HH:mm:ss")

    return @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>$Description</Description>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>$UserId</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <Enabled>true</Enabled>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <ExecutionTimeLimit>PT4H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$sb</StartBoundary>
      <ScheduleByMonth>
        <Months>
          <January /><February /><March /><April /><May /><June />
          <July /><August /><September /><October /><November /><December />
        </Months>
        <DaysOfMonth>
          <Day>1</Day>
        </DaysOfMonth>
      </ScheduleByMonth>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>$PowerShellExe</Command>
      <Arguments>$Argument</Arguments>
      <WorkingDirectory>$Root</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@
}

# ===================== ตรวจสิทธิ์ Administrator =====================
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin  = ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  STEP-TASKS : Scheduled Tasks ของ Odoo 19" -ForegroundColor Cyan
Write-Host "  Run as    : $User" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not $isAdmin) {
    Write-Host "`n[ERROR] ต้องรันด้วยสิทธิ์ Administrator" -ForegroundColor Red
    Write-Host "        เปิด PowerShell แบบ Run as Administrator แล้วรันสคริปต์นี้อีกครั้ง" -ForegroundColor Yellow
    if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิด" }
    exit 1
}
Write-Host "`n[OK] Running as Administrator" -ForegroundColor Green

$summary = @()
$hasWarning = $false

try {
    if ($RemoveTasks) {
        foreach ($name in @($TaskStart, $TaskBackup, $TaskDdns)) {
            if (Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue) {
                Unregister-ScheduledTask -TaskName $name -Confirm:$false
                Write-Host "  ลบ task: $name" -ForegroundColor DarkYellow
                $summary += "REMOVED  $name"
            } else {
                Write-Host "  ไม่พบ task: $name (ข้าม)" -ForegroundColor Gray
                $summary += "SKIP     $name (ไม่มีอยู่)"
            }
        }
    } else {
        foreach ($path in @($Step3, $Step4, $Ddns)) {
            if (-not (Test-Path -LiteralPath $path)) { throw "ไม่พบสคริปต์ที่จำเป็น: $path" }
        }

        # ---------- 1. Auto Start (At log on) ----------
        Write-Head "[1/3] $TaskStart"
        $priStart = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Highest
        $actStart = New-OdooTaskAction $Step3 "-NoPause"
        $setStart = New-OdooTaskSettings
        $trgStart = New-ScheduledTaskTrigger -AtLogOn -User $User

        Register-ScheduledTask -TaskName $TaskStart `
            -Action $actStart -Trigger $trgStart -Settings $setStart -Principal $priStart `
            -Description "At log on: start Odoo 19 + Nginx + Cloudflare DDNS (STEP-3-Start-Odoo19.ps1)" `
            -Force | Out-Null
        Write-Host "  ตั้งค่าแล้ว: At log on ($User) -> STEP-3, RunLevel Highest" -ForegroundColor Green
        $summary += "OK       $TaskStart (AtLogOn -> STEP-3)"

        # ---------- 2. Monthly Backup (run whether logged on or not) ----------
        Write-Head "[2/3] $TaskBackup"
        $priBackup = New-ScheduledTaskPrincipal -UserId $User -LogonType S4U -RunLevel Highest
        $actBackup = New-OdooTaskAction $Step4 "-Database odoo19_pdev"
        $setBackup = New-OdooTaskSettings

        $existingBackup = Get-ScheduledTask -TaskName $TaskBackup -ErrorAction SilentlyContinue
        if ($existingBackup) {
            Set-ScheduledTask -TaskName $TaskBackup -Action $actBackup -Principal $priBackup -Settings $setBackup | Out-Null
            Write-Host "  ปรับ task เดิม: action -> STEP-4, logon type -> S4U (ไม่ต้องเก็บรหัสผ่าน)" -ForegroundColor Green
            Write-Host "  trigger เดิมยังคงอยู่ (วันที่ 1 ของทุกเดือน)" -ForegroundColor Gray
            $summary += "OK       $TaskBackup (logon type -> S4U, action -> STEP-4)"
        } else {
            if ($TriggerTime -notmatch '^\d{1,2}:\d{2}$') {
                throw "รูปแบบ -TriggerTime ต้องเป็น HH:mm (เช่น 03:00) แต่ได้รับ: $TriggerTime"
            }

            $xml = New-OdooMonthlyTaskXml -UserId $User -Time $TriggerTime `
                -Argument $actBackup.Arguments `
                -Description "Monthly database backup of odoo19_pdev (STEP-4-Backup-Odoo19.ps1)"
            Register-ScheduledTask -TaskName $TaskBackup -Xml $xml -Force | Out-Null
            Write-Host "  สร้าง task ใหม่: วันที่ 1 ของทุกเดือน เวลา $TriggerTime -> STEP-4, logon type S4U" -ForegroundColor Green
            $summary += "OK       $TaskBackup (สร้างใหม่ monthly $TriggerTime)"
        }

        # ---------- ตรวจสอบผลงาน backup ให้ตรงตามเงื่อนไข ----------
        $backupXml = Export-ScheduledTask -TaskName $TaskBackup
        $checks = @(
            @{ Name = "logon type = S4U (รันได้แม้ไม่มีใครล็อกอิน)"; Ok = ($backupXml -match '<LogonType>S4U</LogonType>') },
            @{ Name = "trigger = วันที่ 1 ของทุกเดือน";               Ok = ($backupXml -match '<Day>1</Day>') },
            @{ Name = "action -> STEP-4-Backup-Odoo19.ps1";            Ok = ($backupXml -match 'STEP-4-Backup-Odoo19\.ps1') },
            @{ Name = "ไม่บล็อกเมื่อใช้แบตเตอรี่";                      Ok = (($backupXml -match '<DisallowStartIfOnBatteries>false') -and ($backupXml -match '<StopIfGoingOnBatteries>false')) }
        )
        foreach ($c in $checks) {
            if ($c.Ok) {
                Write-Host "    [OK]   $($c.Name)" -ForegroundColor Green
            } else {
                Write-Host "    [WARN] $($c.Name)" -ForegroundColor Yellow
                $hasWarning = $true
            }
        }

        # ---------- 3. Cloudflare DDNS ----------
        Write-Head "[3/3] $TaskDdns"
        $actDdns = New-OdooTaskAction $Ddns ""
        $existingDdns = Get-ScheduledTask -TaskName $TaskDdns -ErrorAction SilentlyContinue
        if ($existingDdns) {
            Set-ScheduledTask -TaskName $TaskDdns -Action $actDdns | Out-Null
            Write-Host "  ปรับ task เดิม: action -> STEP-DDNS-Cloudflare-Odoo19.ps1" -ForegroundColor Green
            Write-Host "  trigger เดิมยังคงอยู่ (ทุก 5 นาที)" -ForegroundColor Gray
            $summary += "OK       $TaskDdns (action -> STEP-DDNS)"
        } else {
            $trgDdns = New-ScheduledTaskTrigger -Once -At (Get-Date) `
                -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)
            $priDdns = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Highest
            Register-ScheduledTask -TaskName $TaskDdns `
                -Action $actDdns -Trigger $trgDdns -Settings (New-OdooTaskSettings) -Principal $priDdns `
                -Description "Cloudflare DDNS update for pdev-erp.auto-info.com (STEP-DDNS-Cloudflare-Odoo19.ps1)" `
                -Force | Out-Null
            Write-Host "  สร้าง task ใหม่: ทุก 5 นาที -> STEP-DDNS" -ForegroundColor Green
            $summary += "OK       $TaskDdns (สร้างใหม่ ทุก 5 นาที)"
        }
    }

    # ---------- สรุปผล ----------
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  สรุปผล" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    foreach ($line in $summary) { Write-Host "  $line" -ForegroundColor White }

    Write-Host "`n--- สถานะ task ปัจจุบัน ---" -ForegroundColor Gray
    Get-ScheduledTask | Where-Object { $_.TaskName -in @($TaskStart, $TaskBackup, $TaskDdns) } | ForEach-Object {
        Write-Host ("  {0,-28} [{1}]  logonType={2}  runLevel={3}" -f `
            $_.TaskName, $_.State, $_.Principal.LogonType, $_.Principal.RunLevel) -ForegroundColor Gray
    }

    if ($RemoveTasks) {
        Write-Host "`nลบ task ทั้ง 3 ตัวเรียบร้อย" -ForegroundColor Green
    } elseif ($hasWarning) {
        Write-Host "`nSTEP-TASKS เสร็จสิ้น แต่มีข้อที่ไม่ผ่านการตรวจสอบ (ดู [WARN] ด้านบน)" -ForegroundColor Yellow
    } else {
        Write-Host "`nSTEP-TASKS เสร็จสิ้นสมบูรณ์" -ForegroundColor Green
    }
} catch {
    Write-Host "`n[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if ($NoPause) { throw }
    exit 1
} finally {
    if (-not $NoPause) { Read-Host "`nกด Enter เพื่อปิดหน้าต่างนี้" }
}
