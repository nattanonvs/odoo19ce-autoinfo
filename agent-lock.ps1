<#
.SYNOPSIS
    Resource-Scoped Lease สำหรับประสานงาน AI agent หลายตัวให้ทำงานขนานได้อย่างปลอดภัย
    (แทนกลไก Single-writer เดิม — ดู AGENTS.md ข้อ 2)

.DESCRIPTION
    จับ / ปล่อย / ตรวจสอบ / ต่ออายุ lease ของทรัพยากรที่ "เขียนร่วมกันไม่ได้" (Tier 2)
    เช่น db:odoo19_pdev, port:8070, ref:refs/heads/19.0, git:gc, file:AGENTS.md

    กลไกความปลอดภัย:
      - Acquire ใช้ FileMode::CreateNew (atomic) -> ถ้าสร้างได้ = ได้สิทธิ์แต่ผู้เดียว
      - lease ถือว่า "หมดอายุ" เมื่อ now - heartbeat_at > ttl_seconds
      - เขียนทับ (break) ได้เฉพาะเมื่อ "หมดอายุ" และ PID เจ้าของ "ตายแล้ว" เท่านั้น
      - Heartbeat / Release ต้องเป็นเจ้าของ (agent_id ตรงกัน) เท่านั้น

    รหัสออก (exit code):
      0 = สำเร็จ
      3 = ทรัพยากรไม่ว่าง (มีเจ้าของที่ยังมีชีวิต) -> agent ต้องหยุด/รอ/เปลี่ยน resource ของตัวเอง
      4 = ไม่มีสิทธิ์ (ไม่ใช่เจ้าของ lease) หรือไม่พบ lease

.PARAMETER Action
    Acquire | Release | Status | Heartbeat

.PARAMETER Resource
    resource key รูปแบบ <type>:<name> เช่น db:odoo19_pdev (จำเป็นสำหรับทุก Action ยกเว้น Status)

.PARAMETER AgentId
    รหัส agent (ค่าเริ่มต้นอ่านจากตัวแปรสภาพแวดล้อม AGENT_ID)

.PARAMETER Ttl
    อายุ lease เป็นวินาที (ค่าเริ่มต้น 300)

.PARAMETER Purpose
    คำอธิบายสั้น ๆ ว่างานนี้ทำอะไร (บันทึกในไฟล์ lease เพื่อให้ agent อื่นเห็น)

.PARAMETER OwnerPid
    PID ที่จะบันทึกเป็นเจ้าของ lease (ค่าเริ่มต้น = PID ของ process แม่ผู้เรียกสคริปต์นี้)
    ระบุเองกรณีที่ process แม่ไม่ใช่ process ที่มีอายุยาวตลอดงาน

.EXAMPLE
    pwsh -File .\agent-lock.ps1 -Action Status

.EXAMPLE
    pwsh -File .\agent-lock.ps1 -Action Acquire -Resource db:odoo19_pdev `
        -AgentId codex-od19_ai_assistant -Purpose "upgrade module" -Ttl 900

.EXAMPLE
    pwsh -File .\agent-lock.ps1 -Action Release -Resource db:odoo19_pdev -AgentId codex-od19_ai_assistant
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('Acquire', 'Release', 'Status', 'Heartbeat')]
    [string]$Action,

    [string]$Resource,
    [string]$AgentId = $env:AGENT_ID,
    [int]$Ttl = 300,
    [string]$Purpose = '',
    [int]$OwnerPid = 0
)

$ErrorActionPreference = 'Stop'

$Root     = $PSScriptRoot
$ExitOk   = 0
$ExitBusy = 3
$ExitDeny = 4

function Resolve-LockDir {
    # ทะเบียน lease ต้องใช้ร่วมกัน "ทุก worktree" ของ repo เดียวกัน
    # จึงเก็บที่ <main-repo-root>/.agent-locks
    # (ถ้าเก็บที่ $PSScriptRoot งานคนละ worktree จะเห็น lock คนละชุด = ประสานงานไม่ได้)
    try {
        $common = (& git -C $Root rev-parse --path-format=absolute --git-common-dir 2>$null)
        if ($LASTEXITCODE -eq 0 -and $common) {
            $main = Split-Path -Parent ([string]$common).Trim()
            if ($main) { return (Join-Path $main '.agent-locks') }
        }
    } catch { }
    return (Join-Path $Root '.agent-locks')
}

$LockDir = Resolve-LockDir

function Get-LeasePath {
    param([string]$Key)
    $safe = $Key -replace '[^A-Za-z0-9._-]', '-'
    return (Join-Path $LockDir ("{0}.lock" -f $safe))
}

function Test-PidAlive {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    return [bool](Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Read-Lease {
    param([string]$Path)
    try {
        return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Test-LeaseExpired {
    param($Lease)
    $ttl = if ($Lease.ttl_seconds) { [int]$Lease.ttl_seconds } else { $Ttl }
    try {
        $hb  = ([datetimeoffset]::Parse([string]$Lease.heartbeat_at)).ToUniversalTime()
        $age = ([datetimeoffset]::UtcNow - $hb).TotalSeconds
        return ($age -gt $ttl)
    } catch {
        return $true
    }
}

function Resolve-OwnerPid {
    if ($OwnerPid -gt 0) { return $OwnerPid }
    try {
        $me = Get-CimInstance -ClassName Win32_Process -Filter ("ProcessId={0}" -f $PID) -ErrorAction Stop
        if ($me -and $me.ParentProcessId) { return [int]$me.ParentProcessId }
    } catch { }
    return $PID
}

function New-LeaseFile {
    # คืนค่า $true เมื่อสร้างไฟล์สำเร็จแบบ atomic, $false เมื่อมีไฟล์อยู่แล้ว
    param([string]$Path, [string]$Content)
    try {
        $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    } catch [System.IO.IOException] {
        return $false
    }
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Content)
        $fs.Write($bytes, 0, $bytes.Length)
        $fs.Flush()
    } finally {
        $fs.Dispose()
    }
    return $true
}

function Get-BranchName {
    try {
        $b = (& git rev-parse --abbrev-ref HEAD 2>$null)
        if ($b) { return ([string]$b).Trim() }
    } catch { }
    return ''
}

function Invoke-Acquire {
    if (-not $Resource) { throw 'ต้องระบุ -Resource สำหรับ Acquire' }
    if (-not $AgentId)  { throw 'ต้องระบุ -AgentId (หรือตั้งตัวแปรสภาพแวดล้อม AGENT_ID)' }
    if (-not (Test-Path -LiteralPath $LockDir)) {
        New-Item -ItemType Directory -Path $LockDir -Force | Out-Null
    }

    $path  = Get-LeasePath $Resource
    $owner = Resolve-OwnerPid
    $now   = [datetimeoffset]::Now
    $body  = [ordered]@{
        resource     = $Resource
        agent_id     = $AgentId
        branch       = Get-BranchName
        pid          = $owner
        purpose      = $Purpose
        acquired_at  = $now.ToString('o')
        ttl_seconds  = $Ttl
        heartbeat_at = $now.ToString('o')
    } | ConvertTo-Json

    if (New-LeaseFile -Path $path -Content $body) {
        Write-Host ("LEASE: acquired '{0}' by {1} (pid {2}, ttl {3}s)" -f $Resource, $AgentId, $owner, $Ttl) -ForegroundColor Green
        exit $ExitOk
    }

    # มีไฟล์อยู่แล้ว -> ตรวจเจ้าของ
    $existing = Read-Lease $path
    if ($null -eq $existing) {
        Write-Host ("LEASE: ไฟล์ lock อ่านไม่ได้/เสียหาย -> {0}" -f $path) -ForegroundColor Red
        Write-Host 'LEASE: หยุดเพื่อความปลอดภัย ห้ามลบเอง ให้รายงานผู้ใช้' -ForegroundColor Red
        exit $ExitBusy
    }

    $alive   = Test-PidAlive $existing.pid
    $expired = Test-LeaseExpired $existing

    if ($expired -and -not $alive) {
        Write-Host ("LEASE: break lease หมดอายุของ {0} (pid {1})" -f $existing.agent_id, $existing.pid) -ForegroundColor Yellow
        Remove-Item -LiteralPath $path -Force
        if (New-LeaseFile -Path $path -Content $body) {
            Write-Host ("LEASE: acquired '{0}' by {1} (pid {2}, ttl {3}s)" -f $Resource, $AgentId, $owner, $Ttl) -ForegroundColor Green
            exit $ExitOk
        }
    }

    Write-Host ("LEASE: '{0}' ไม่ว่าง — ถือโดย {1} (pid {2}, alive={3}, heartbeat {4})" -f `
        $Resource, $existing.agent_id, $existing.pid, $alive, $existing.heartbeat_at) -ForegroundColor Red
    Write-Host 'LEASE: หยุด/รอ หรือเปลี่ยน resource ของตัวเอง' -ForegroundColor Red
    exit $ExitBusy
}

function Invoke-Heartbeat {
    if (-not $Resource) { throw 'ต้องระบุ -Resource สำหรับ Heartbeat' }
    $path = Get-LeasePath $Resource
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host ("LEASE: ไม่พบ lease '{0}'" -f $Resource) -ForegroundColor Red
        exit $ExitDeny
    }
    $lease = Read-Lease $path
    if ($null -eq $lease -or $lease.agent_id -ne $AgentId) {
        Write-Host ("LEASE: ไม่ใช่เจ้าของ '{0}' — ห้ามแก้ lease ของ agent อื่น" -f $Resource) -ForegroundColor Red
        exit $ExitDeny
    }
    $lease.heartbeat_at = [datetimeoffset]::Now.ToString('o')
    ($lease | ConvertTo-Json) | Set-Content -LiteralPath $path -Encoding utf8
    Write-Host ("LEASE: heartbeat '{0}' ({1})" -f $Resource, $lease.heartbeat_at) -ForegroundColor Green
    exit $ExitOk
}

function Invoke-Release {
    if (-not $Resource) { throw 'ต้องระบุ -Resource สำหรับ Release' }
    $path = Get-LeasePath $Resource
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host ("LEASE: ไม่มี lease ของ '{0}' ให้ปล่อย" -f $Resource) -ForegroundColor DarkGray
        exit $ExitOk
    }
    $lease = Read-Lease $path
    if ($lease -and $lease.agent_id -ne $AgentId) {
        Write-Host ("LEASE: '{0}' เป็นของ {1} — ห้ามปล่อยแทน" -f $Resource, $lease.agent_id) -ForegroundColor Red
        exit $ExitDeny
    }
    Remove-Item -LiteralPath $path -Force
    Write-Host ("LEASE: released '{0}'" -f $Resource) -ForegroundColor Green
    exit $ExitOk
}

function Invoke-Status {
    if (-not (Test-Path -LiteralPath $LockDir)) {
        Write-Host 'LEASE: ไม่มี lease ใด ๆ (ว่างทั้งหมด)' -ForegroundColor DarkGray
        exit $ExitOk
    }
    $files = @(Get-ChildItem -LiteralPath $LockDir -Filter '*.lock' -File -ErrorAction SilentlyContinue)
    if ($files.Count -eq 0) {
        Write-Host 'LEASE: ไม่มี lease ใด ๆ (ว่างทั้งหมด)' -ForegroundColor DarkGray
        exit $ExitOk
    }

    $rows = foreach ($f in $files) {
        $l = Read-Lease $f.FullName
        if ($null -eq $l) {
            [pscustomobject]@{
                Resource = $f.BaseName; Agent = '(เสียหาย)'; Pid = ''
                Alive = '?'; Age_s = ''; Ttl_s = ''; Stale = '?'
            }
            continue
        }
        $alive   = Test-PidAlive $l.pid
        $expired = Test-LeaseExpired $l
        $age = try {
            [int]([datetimeoffset]::UtcNow - ([datetimeoffset]::Parse([string]$l.heartbeat_at)).ToUniversalTime()).TotalSeconds
        } catch { '' }
        [pscustomobject]@{
            Resource = $l.resource
            Agent    = $l.agent_id
            Pid      = $l.pid
            Alive    = $alive
            Age_s    = $age
            Ttl_s    = $l.ttl_seconds
            Stale    = ($expired -and -not $alive)
        }
    }

    Write-Host 'LEASE: รายการที่ถูกถืออยู่' -ForegroundColor Cyan
    $rows | Format-Table -AutoSize | Out-String | Write-Host
    exit $ExitOk
}

switch ($Action) {
    'Acquire'   { Invoke-Acquire }
    'Release'   { Invoke-Release }
    'Heartbeat' { Invoke-Heartbeat }
    'Status'    { Invoke-Status }
}
