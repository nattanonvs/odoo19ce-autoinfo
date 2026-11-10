<#
.SYNOPSIS
    od19-health-watch : สคริปต์เฝ้าระวังสุขภาพ Odoo 19 แบบ "ชั้นนอก" (P1 Early Warning)

.DESCRIPTION
    ตัวเฝ้าระวังที่รัน "นอก" กระบวนการ Odoo (คนละ process) เพื่อจับเหตุที่ Odoo
    รายงานตัวเองไม่ได้ เช่น Odoo ล่ม, PostgreSQL หยุด, งานตามเวลาล้ม/ค้าง, ดิสก์ใกล้เต็ม,
    backup ขาด, และ log มี ERROR/CRITICAL ใหม่

    หลักการ (สอดคล้องข้อเสนอโครงการ ข้อ 1 และ AGENTS.md)
      - อ่านอย่างเดียว (read-only) ไม่เขียนทับข้อมูลธุรกิจ
      - ไม่ restart / ไม่ปิดบริการใด ๆ อัตโนมัติ (D5: ไม่อนุญาตใน P1-P3)
      - local-first: ค่าเริ่มต้นเก็บผลในเครื่อง ไม่ส่งออกนอกเครื่อง
      - ทนต่อความล้มเหลวของตัวเอง: เขียน heartbeat ทุกครั้งที่รัน (dead-man switch)
      - กันสัญญาณซ้ำ (dedup) ด้วย fingerprint + ช่วงเวลา cooldown

    การตรวจในรอบเดียว (7 อย่าง ตามสเปก P1)
      1. TCP/HTTP : http_port ตอบ HTTP 200 ที่ /web/login, longpolling, db_port, :80
      2. Service  : postgresql-x64-16, Nginx (:80)
      3. Scheduled Task : ผลรันล่าสุด + อายุการรันล่าสุดของงานหลัก (Auto Start / Backup / DDNS)
      4. Log      : นับ ERROR/CRITICAL เฉพาะส่วนที่เพิ่มใหม่ (จำ offset) + แนบตัวอย่าง 3 บรรทัด
      5. ดิสก์     : เตือน < -DiskWarnGB, วิกฤต < -DiskCritGB
      6. Backup   : ล่าสุดเกิน -BackupWarnHours = เตือน, เกิน -BackupCritDays = วิกฤต
      7. Dead-man : เขียน heartbeat ของตัวเองทุกครั้งที่รัน

    ผลลัพธ์
      - logs\health\health-watch.log   : บันทึกการรันแบบอ่านง่าย
      - logs\health\alerts.jsonl       : สัญญาณเตือนแบบมีโครงสร้าง (JSON Lines)
      - logs\health\state.json         : สถานะสะสม (log offset, fingerprint ที่แจ้งล่าสุด)
      - logs\health\heartbeat.json     : สัญญาณ "ตัวเฝ้ายังมีชีวิต" (ให้ชั้นในตรวจต่อใน P2)
      - exit code                      : 0=ปกติ, 1=เตือน(WARN), 2=วิกฤต(CRIT)

.EXAMPLE
    pwsh -NoProfile -File .\od19-health-watch.ps1
    # รันแบบเห็นรายงานบนจอ (ใช้ตอนตรวจด้วยตา)

.EXAMPLE
    pwsh -NoProfile -File .\od19-health-watch.ps1 -Quiet
    # รันแบบเงียบ สำหรับ Task Scheduler (เขียนลงไฟล์เท่านั้น)

.EXAMPLE
    pwsh -NoProfile -File .\od19-health-watch.ps1 -Root C:\odoo-dev\odoo19
    # ชี้ไปที่รากโปรเจกต์จริง (ใช้ตอนทดสอบสคริปต์จาก worktree อื่น)

.EXAMPLE
    pwsh -NoProfile -File .\od19-health-watch.ps1 -SimulateDown
    # ยิงเหตุจำลองเพื่อทดสอบเส้นทาง alert โดยไม่แตะบริการจริง (read-only ทั้งหมด)

.NOTES
    AGENT_ID : trae-od19_monitor
    เฟส     : P1 (System Health & Early Warning)
#>
[CmdletBinding()]
param(
    [string]$Root = $PSScriptRoot,

    # ลดการพิมพ์บนจอ (สำหรับ Scheduled Task)
    [switch]$Quiet,

    # ยิงเหตุจำลองระดับ CRIT เพื่อทดสอบเส้นทาง alert (ไม่แตะบริการจริง)
    [switch]$SimulateDown,

    # เกณฑ์
    [int]$DiskWarnGB = 20,
    [int]$DiskCritGB = 10,
    [int]$BackupWarnHours = 25,
    [int]$BackupCritDays = 7,
    [int]$AlertCooldownMinutes = 30,
    [int]$ServiceStaleDays = 30,   # งานที่ trigger ตอน logon (Auto Start) ปล่อยอายุได้ยาวกว่า

    # ช่องทางสำรอง (ไม่บังคับ) — webhook (เช่น LINE) ถ้าไม่ตั้งจะเก็บในเครื่องเท่านั้น
    [string]$NotifyUri = ''
)

$ErrorActionPreference = 'Continue'
$sep = '=' * 64
$script:Version = '1.0.0'
$script:AgentId = 'trae-od19_monitor'

$now      = Get-Date
$stamp    = $now.ToString('yyyy-MM-dd HH:mm:ss')
$stateDir = Join-Path $Root 'logs\health'
if (-not (Test-Path -LiteralPath $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}
$stateFile     = Join-Path $stateDir 'state.json'
$alertFile     = Join-Path $stateDir 'alerts.jsonl'
$alertLogFile  = Join-Path $stateDir 'alerts.log'
$runLogFile    = Join-Path $stateDir 'health-watch.log'
$heartbeatFile = Join-Path $stateDir 'heartbeat.json'
$queueFile     = Join-Path $stateDir 'alerts.queue.jsonl'

# เขียนไฟล์แบบ UTF-8 no-BOM ผ่าน .NET เพื่อให้ผลเหมือนกันทั้ง PowerShell 5.1 และ 7
# (สำคัญกับ JSONL: ถ้ามี BOM แทรกกลางไฟล์จะทำให้อ่านทีละบรรทัดด้วย ConvertFrom-Json พัง)
$script:Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-AllText { param([string]$Path, [string]$Text) [System.IO.File]::WriteAllText($Path, $Text, $script:Utf8NoBom) }
function Add-Line { param([string]$Path, [string]$Text) [System.IO.File]::AppendAllText($Path, $Text + "`r`n", $script:Utf8NoBom) }

# ---------------------------------------------------------------- helpers

function Read-OdooConf {
    param([string]$Path)
    $values = @{}
    if (Test-Path -LiteralPath $Path) {
        foreach ($line in Get-Content -LiteralPath $Path) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
                $values[$Matches[1]] = $Matches[2].Trim()
            }
        }
    }
    return $values
}

# ตรวจว่าพอร์ต "เชื่อมต่อได้จริง" ด้วย TCP connect
# เหตุผล: การ enumerate listening socket (Get-NetTCPConnection / netstat) ไม่น่าเชื่อถือ
#         ในบางสภาพแวดล้อม (ถูกกรอง/ไม่มีสิทธิ์มองเห็น) จึงยิง TCP connect ตรง ๆ ซึ่งสะท้อนความจริง
function Test-Tcp {
    param([string]$ComputerName = '127.0.0.1', [int]$Port, [int]$TimeoutMs = 2000)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($ComputerName, $Port, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs)) { $client.Close(); return $false }
        $client.EndConnect($iar)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Test-Http {
    param([string]$Url, [int]$TimeoutSec = 8, [int]$Retries = 2)
    # ลองซ้ำได้: ครั้งแรกอาจช้าเพราะ Odoo กำลังทำงานหนัก (asset bundle / lock ir_attachment)
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            if ((Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec).StatusCode -eq 200) { return $true }
        } catch {
            # ไม่ throw ต่อ — ให้ลองรอบถัดไป แล้วค่อยสรุปว่าไม่ผ่าน
        }
        if ($i -lt $Retries) { Start-Sleep -Seconds 2 }
    }
    return $false
}

$script:Findings = New-Object System.Collections.Generic.List[object]
function Add-Finding {
    param([string]$Id, [ValidateSet('OK', 'WARN', 'CRIT')][string]$Level, [string]$Detail)
    $script:Findings.Add([pscustomobject]@{ Id = $Id; Level = $Level; Detail = $Detail })
    if (-not $Quiet) {
        $color = switch ($Level) { 'OK' { 'Green' } 'WARN' { 'DarkYellow' } 'CRIT' { 'Red' } }
        Write-Host ("  [{0,-4}] {1,-26} : {2}" -f $Level, $Id, $Detail) -ForegroundColor $color
    }
}

function Get-OverallLevel {
    $levels = @($script:Findings | ForEach-Object { $_.Level })
    if ($levels -contains 'CRIT') { return 'CRIT' }
    if ($levels -contains 'WARN') { return 'WARN' }
    return 'OK'
}

# ---------------------------------------------------------------- state

$state = @{ log_offset = 0; last_run = $null; alerts = @() }
if (Test-Path -LiteralPath $stateFile) {
    try { $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json } catch { }
}
if ($null -eq $state) { $state = [pscustomobject]@{ log_offset = 0; last_run = $null; alerts = @() } }

# ---------------------------------------------------------------- config

$confFile = Join-Path $Root 'odoo.conf'
$conf     = Read-OdooConf -Path $confFile

$httpPort  = if ($conf['http_port']) { [int]$conf['http_port'] } else { 8070 }
$workers   = if ($conf['workers']) { [int]$conf['workers'] } else { 0 }
$lpPort    = if ($conf['gevent_port']) { [int]$conf['gevent_port'] } else { $httpPort + 2 }
$dbPort    = if ($conf['db_port']) { [int]$conf['db_port'] } else { 5432 }
$nginxPort = 80
$dbName    = if ($conf['db_name']) { $conf['db_name'] } else { 'odoo19_pdev' }
$logPath   = if ($conf['logfile']) { $conf['logfile'] } else { Join-Path $Root 'odoo_server.log' }

if (-not $Quiet) {
    Write-Host $sep
    Write-Host (' Odoo 19 Health Watch  v{0}   {1}' -f $script:Version, $stamp) -ForegroundColor Cyan
    Write-Host (' root : {0}' -f $Root)
    Write-Host (' conf : {0} {1}' -f $confFile, $(if (Test-Path -LiteralPath $confFile) { '(found)' } else { '(NOT found - using defaults)' }))
    Write-Host $sep
    Write-Host "`n[1] TCP / HTTP" -ForegroundColor Yellow
}

# ---------------------------------------------------------------- 1. TCP / HTTP

# ใช้ 127.0.0.1 แทน localhost เพื่อเลี่ยงการ resolve ไป ::1 (Odoo bind เฉพาะ IPv4)
$httpOk = Test-Http -Url ("http://127.0.0.1:{0}/web/login" -f $httpPort)
if ($SimulateDown) { $httpOk = $false }
if ($httpOk) {
    Add-Finding -Id 'http:web_login' -Level 'OK' -Detail ("HTTP 200 at /web/login (:{0})" -f $httpPort)
} else {
    Add-Finding -Id 'http:web_login' -Level 'CRIT' -Detail ("no HTTP 200 at :{0}/web/login" -f $httpPort)
}

# longpolling/gevent จะถูก bind เป็นพอร์ตแยก "เฉพาะเมื่อ workers > 0"
# เมื่อ workers = 0 (threaded) Odoo ให้บริการ longpolling บนพอร์ต HTTP เดียวกัน จึงไม่ต้องตรวจพอร์ตแยก
if ($workers -gt 0) {
    $up = Test-Tcp -Port $lpPort
    Add-Finding -Id 'tcp:longpolling' -Level $(if ($up) { 'OK' } else { 'CRIT' }) -Detail ("port :{0} {1}" -f $lpPort, $(if ($up) { 'reachable' } else { 'NOT reachable' }))
} else {
    Add-Finding -Id 'tcp:longpolling' -Level 'OK' -Detail ("N/A (workers=0, served on :{0})" -f $httpPort)
}

foreach ($p in @(
        @{ Port = $dbPort;    Id = 'tcp:postgresql' },
        @{ Port = $nginxPort; Id = 'tcp:nginx' })) {
    $up = Test-Tcp -Port $p.Port
    if ($SimulateDown -and $p.Id -eq 'tcp:postgresql') { $up = $false }
    Add-Finding -Id $p.Id -Level $(if ($up) { 'OK' } else { 'CRIT' }) -Detail ("port :{0} {1}" -f $p.Port, $(if ($up) { 'reachable' } else { 'NOT reachable' }))
}

# ---------------------------------------------------------------- 2. Services

if (-not $Quiet) { Write-Host "`n[2] Services" -ForegroundColor Yellow }

$pgSvc = Get-Service -Name 'postgresql-x64-16' -ErrorAction SilentlyContinue
if ($pgSvc) {
    Add-Finding -Id 'svc:postgresql' -Level $(if ($pgSvc.Status -eq 'Running') { 'OK' } else { 'CRIT' }) -Detail ("postgresql-x64-16 = {0}" -f $pgSvc.Status)
} else {
    Add-Finding -Id 'svc:postgresql' -Level 'WARN' -Detail 'service postgresql-x64-16 not found'
}

$nginxProc = @(Get-Process -Name 'nginx' -ErrorAction SilentlyContinue)
if ($nginxProc.Count -gt 0) {
    Add-Finding -Id 'svc:nginx' -Level 'OK' -Detail ("nginx running ({0} proc)" -f $nginxProc.Count)
} else {
    Add-Finding -Id 'svc:nginx' -Level 'CRIT' -Detail 'nginx process not running'
}

# ---------------------------------------------------------------- 3. Scheduled Tasks

if (-not $Quiet) { Write-Host "`n[3] Scheduled Tasks" -ForegroundColor Yellow }

$taskSpecs = @(
    @{ Name = 'Odoo19 Auto Start';        MaxAgeMinutes = ($ServiceStaleDays * 24 * 60) },
    @{ Name = 'Odoo19 Monthly Backup';    MaxAgeMinutes = (35 * 24 * 60) },
    @{ Name = 'Cloudflare DDNS - Odoo19'; MaxAgeMinutes = 60 }
)
foreach ($spec in $taskSpecs) {
    $t = Get-ScheduledTask -TaskName $spec.Name -ErrorAction SilentlyContinue
    if (-not $t) {
        Add-Finding -Id ('task:{0}' -f $spec.Name) -Level 'WARN' -Detail 'task not found'
        continue
    }
    $info = Get-ScheduledTaskInfo -TaskName $spec.Name -ErrorAction SilentlyContinue
    $ageMin = if ($info.LastRunTime) { [int]((New-TimeSpan -Start $info.LastRunTime -End $now).TotalMinutes) } else { $null }
    $badResult = ($info.LastTaskResult -ne 0 -and $info.LastTaskResult -ne $null)

    if ($badResult) {
        Add-Finding -Id ('task:{0}' -f $spec.Name) -Level 'WARN' -Detail ("LastTaskResult={0} (age {1} min)" -f $info.LastTaskResult, $ageMin)
    } elseif ($null -eq $ageMin -or $ageMin -gt $spec.MaxAgeMinutes) {
        Add-Finding -Id ('task:{0}' -f $spec.Name) -Level 'WARN' -Detail ("stale: last run {0} ({1} min ago > {2})" -f $info.LastRunTime, $ageMin, $spec.MaxAgeMinutes)
    } else {
        Add-Finding -Id ('task:{0}' -f $spec.Name) -Level 'OK' -Detail ("last {0}, result=0" -f $info.LastRunTime)
    }
}

# ---------------------------------------------------------------- 4. Log delta

if (-not $Quiet) { Write-Host "`n[4] Log (new ERROR/CRITICAL)" -ForegroundColor Yellow }

$newOffset = [long]$state.log_offset
$errCount  = 0
$critCount = 0
$samples   = @()
if (Test-Path -LiteralPath $logPath) {
    $size = (Get-Item -LiteralPath $logPath).Length
    if ($size -lt $newOffset) { $newOffset = 0 }   # log ถูกหมุน/ตัดทิ้ง
    if ($size -gt $newOffset) {
        try {
            $fs = [System.IO.File]::Open($logPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            $fs.Seek($newOffset, [System.IO.SeekOrigin]::Begin) | Out-Null
            $reader = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
            $chunk  = $reader.ReadToEnd()
            $reader.Close(); $fs.Close()

            # ประมวลผลเฉพาะบรรทัดที่ "ครบ" (จบด้วย newline) เพื่อไม่ให้ offset ผิด
            $lastNl = $chunk.LastIndexOf("`n")
            if ($lastNl -ge 0) {
                $complete = $chunk.Substring(0, $lastNl + 1)
                $newOffset += [System.Text.Encoding]::UTF8.GetByteCount($complete)
                foreach ($ln in ($complete -split "`r?`n")) {
                    if ($ln -match '\sCRITICAL\s') { $critCount++; if ($samples.Count -lt 3) { $samples += $ln.Trim() } }
                    elseif ($ln -match '\sERROR\s') { $errCount++; if ($samples.Count -lt 3) { $samples += $ln.Trim() } }
                }
            }
        } catch {
            Add-Finding -Id 'log:read' -Level 'WARN' -Detail ("cannot read log: {0}" -f $_.Exception.Message)
        }
    }
    if ($critCount -gt 0) {
        Add-Finding -Id 'log:critical' -Level 'CRIT' -Detail ("{0} CRITICAL in new log" -f $critCount)
    } elseif ($errCount -gt 0) {
        Add-Finding -Id 'log:error' -Level 'WARN' -Detail ("{0} ERROR in new log" -f $errCount)
    } else {
        Add-Finding -Id 'log:delta' -Level 'OK' -Detail ("no new ERROR/CRITICAL ({0} bytes scanned)" -f ($size - [long]$state.log_offset))
    }
    if ($samples.Count -gt 0 -and -not $Quiet) {
        foreach ($s in $samples) { Write-Host ("      > {0}" -f ($s.Substring(0, [Math]::Min(160, $s.Length)))) -ForegroundColor DarkGray }
    }
} else {
    Add-Finding -Id 'log:file' -Level 'WARN' -Detail ("log not found: {0}" -f $logPath)
}

# ---------------------------------------------------------------- 5. Disk

if (-not $Quiet) { Write-Host "`n[5] Disk" -ForegroundColor Yellow }

$driveLetter = (Split-Path -Qualifier $Root).TrimEnd(':')
$disk = Get-PSDrive -Name $driveLetter -ErrorAction SilentlyContinue
if ($disk -and $disk.Free -ne $null) {
    $freeGB = [math]::Round($disk.Free / 1GB, 1)
    if ($freeGB -lt $DiskCritGB) {
        Add-Finding -Id 'disk:free' -Level 'CRIT' -Detail ("free {0} GB < {1} GB" -f $freeGB, $DiskCritGB)
    } elseif ($freeGB -lt $DiskWarnGB) {
        Add-Finding -Id 'disk:free' -Level 'WARN' -Detail ("free {0} GB < {1} GB" -f $freeGB, $DiskWarnGB)
    } else {
        Add-Finding -Id 'disk:free' -Level 'OK' -Detail ("free {0} GB on {1}:" -f $freeGB, $driveLetter)
    }
} else {
    Add-Finding -Id 'disk:free' -Level 'WARN' -Detail ("cannot read free space on {0}:" -f $driveLetter)
}

# ---------------------------------------------------------------- 6. Backup freshness

if (-not $Quiet) { Write-Host "`n[6] Backup freshness" -ForegroundColor Yellow }

$backupDir = Join-Path $Root 'backups'
if (Test-Path -LiteralPath $backupDir) {
    $latest = Get-ChildItem -LiteralPath $backupDir -File -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -match '\.(dump|sql|zip|tar\.gz|gz|bak)$' } |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
        $ageH = (New-TimeSpan -Start $latest.LastWriteTime -End $now).TotalHours
        $ageD = $ageH / 24
        if ($ageD -gt $BackupCritDays) {
            Add-Finding -Id 'backup:freshness' -Level 'CRIT' -Detail ("newest backup {0} is {1:N1} h old (> {2} d)" -f $latest.Name, $ageH, $BackupCritDays)
        } elseif ($ageH -gt $BackupWarnHours) {
            Add-Finding -Id 'backup:freshness' -Level 'WARN' -Detail ("newest backup {0} is {1:N1} h old (> {2} h)" -f $latest.Name, $ageH, $BackupWarnHours)
        } else {
            Add-Finding -Id 'backup:freshness' -Level 'OK' -Detail ("newest {0} ({1:N1} h old)" -f $latest.Name, $ageH)
        }
    } else {
        Add-Finding -Id 'backup:freshness' -Level 'CRIT' -Detail 'no backup file found'
    }
} else {
    Add-Finding -Id 'backup:dir' -Level 'WARN' -Detail ("backup dir not found: {0}" -f $backupDir)
}

# ---------------------------------------------------------------- simulate

if ($SimulateDown) {
    Add-Finding -Id 'simulate:down' -Level 'CRIT' -Detail 'SIMULATED DOWN (test alert path; no service touched)'
}

# ---------------------------------------------------------------- 7. Dead-man heartbeat

$overall = Get-OverallLevel
$heartbeat = [pscustomobject]@{
    agent_id   = $script:AgentId
    version    = $script:Version
    host       = $env:COMPUTERNAME
    timestamp  = $now.ToString('o')
    overall    = $overall
    exit_code  = $(switch ($overall) { 'OK' { 0 } 'WARN' { 1 } 'CRIT' { 2 } })
    simulated  = [bool]$SimulateDown
}
Write-AllText -Path $heartbeatFile -Text ($heartbeat | ConvertTo-Json)

# ---------------------------------------------------------------- alerts + dedup

$alerts = @($script:Findings | Where-Object { $_.Level -ne 'OK' })

# fingerprint ของการแจ้งล่าสุดเก็บเป็น "array ของ object" { check, ts }
# เพื่อให้ round-trip ผ่าน JSON ได้ตรงไปตรงมา (hashtable เคยทำให้ค่ากลับมาเพี้ยน)
$prevMap = @{}
if ($state.alerts) {
    foreach ($e in @($state.alerts)) {
        if ($e -and $e.check) { $prevMap[[string]$e.check] = [datetime]$e.ts }
    }
}
$newAlerts = New-Object System.Collections.Generic.List[object]
foreach ($a in $alerts) {
    $fp = $a.Id
    $suppress = $false
    if ($prevMap.ContainsKey($fp)) {
        $ageMin = ($now - $prevMap[$fp]).TotalMinutes
        if ($ageMin -lt $AlertCooldownMinutes) { $suppress = $true }
    }
    if (-not $suppress) {
        $record = [pscustomobject]@{
            ts        = $now.ToString('o')
            agent_id  = $script:AgentId
            level     = $a.Level
            check     = $a.Id
            detail    = $a.Detail
            host      = $env:COMPUTERNAME
            heartbeat = $heartbeatFile
        }
        $newAlerts.Add($record)
        $prevMap[$fp] = $now
        Add-Line -Path $alertFile -Text ($record | ConvertTo-Json -Compress)
        Add-Line -Path $alertLogFile -Text ('{0}  [{1,-4}] {2} : {3}' -f $now.ToString('yyyy-MM-dd HH:mm:ss'), $a.Level, $a.Id, $a.Detail)
    }
}

# ---------------------------------------------------------------- optional webhook (+ offline queue)

if ($NotifyUri) {
    $pending = New-Object System.Collections.Generic.List[string]
    if (Test-Path -LiteralPath $queueFile) {
        Get-Content -LiteralPath $queueFile -ErrorAction SilentlyContinue | Where-Object { $_.Trim() } | ForEach-Object { $pending.Add($_) }
    }
    foreach ($r in $newAlerts) { $pending.Add(($r | ConvertTo-Json -Compress)) }

    $unflushed = New-Object System.Collections.Generic.List[string]
    foreach ($payload in $pending) {
        try {
            Invoke-RestMethod -Uri $NotifyUri -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 10 | Out-Null
        } catch {
            $unflushed.Add($payload)
        }
    }
    if ($unflushed.Count -gt 0) {
        Write-AllText -Path $queueFile -Text ($unflushed -join "`r`n")
    } elseif (Test-Path -LiteralPath $queueFile) {
        Remove-Item -LiteralPath $queueFile -Force -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------- persist state

$alertState = @()
foreach ($k in $prevMap.Keys) {
    $alertState += [pscustomobject]@{ check = [string]$k; ts = $prevMap[$k].ToString('o') }
}
$stateOut = [pscustomobject]@{
    log_offset = $newOffset
    last_run   = $now.ToString('o')
    alerts     = $alertState
}
Write-AllText -Path $stateFile -Text ($stateOut | ConvertTo-Json -Depth 4)

# ---------------------------------------------------------------- run log + summary

$summary = '{0}  overall={1}  checks={2}  new_alerts={3}  simulated={4}' -f `
    $now.ToString('yyyy-MM-dd HH:mm:ss'), $overall, $script:Findings.Count, $newAlerts.Count, [bool]$SimulateDown
Add-Line -Path $runLogFile -Text $summary

if (-not $Quiet) {
    Write-Host "`n$sep"
    $color = switch ($overall) { 'OK' { 'Green' } 'WARN' { 'DarkYellow' } 'CRIT' { 'Red' } }
    Write-Host (" OVERALL : {0}   (findings={1}, new alerts={2})" -f $overall, $script:Findings.Count, $newAlerts.Count) -ForegroundColor $color
    Write-Host (" state   : {0}" -f $stateDir)
    Write-Host $sep
}

exit $(switch ($overall) { 'OK' { 0 } 'WARN' { 1 } 'CRIT' { 2 } })
