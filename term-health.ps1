<#
.SYNOPSIS
    Terminal health check + safe cleanup for the Odoo 19 dev box.

.DESCRIPTION
    Reports PowerShell/encoding state, shell and dev process load, and the ports
    the Odoo stack uses. Read-only by default.
    With -Clean it stops stale PowerShell hosts that are NOT part of the current
    session (self and its ancestors are always spared).
    With -Reclaim it stops an odoo_ls_server (Odoo language server) instance that
    grew past -LsMaxMB; the Trae Odoo extension respawns it when needed.

.EXAMPLE
    .\term-health.ps1
    .\term-health.ps1 -Clean
    .\term-health.ps1 -Clean -StaleMinutes 15
    .\term-health.ps1 -Reclaim
    .\term-health.ps1 -Reclaim -LsMaxMB 1000
#>
[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$Reclaim,
    [int]$StaleMinutes = 30,
    [int]$LsMaxMB = 1500
)

$ErrorActionPreference = 'Continue'
$sep = '=' * 64

function Get-AncestorIds {
    param([int]$StartPid)
    $ids = New-Object System.Collections.Generic.HashSet[int]
    $cur = $StartPid
    while ($cur -and $cur -gt 0) {
        $null = $ids.Add($cur)
        $p = Get-CimInstance Win32_Process -Filter "ProcessId = $cur" -ErrorAction SilentlyContinue
        if (-not $p) { break }
        $cur = [int]$p.ParentProcessId
    }
    return $ids
}

Write-Host $sep
Write-Host ' Terminal Health Check - Odoo 19 dev box' -ForegroundColor Cyan
Write-Host $sep

Write-Host "`n[Shell]" -ForegroundColor Yellow
Write-Host ("  PowerShell    : {0} ({1})" -f $PSVersionTable.PSVersion, $PSVersionTable.PSEdition)
Write-Host ("  Console enc   : {0}" -f [Console]::OutputEncoding.WebName)
Write-Host ("  Code page     : {0}" -f (('' + (chcp)) -replace '[^0-9]', ''))
Write-Host ("  Profile       : {0}" -f $PROFILE)
Write-Host ("  Profile found : {0}" -f (Test-Path -LiteralPath $PROFILE))

Write-Host "`n[Process load]" -ForegroundColor Yellow
$watch = @(
    @{ Label = 'pwsh (shell hosts)'; Stem = 'pwsh' }
    @{ Label = 'node (Trae / JS)';   Stem = 'node' }
    @{ Label = 'python (Odoo)';      Stem = 'python' }
    @{ Label = 'postgres (DB)';      Stem = 'postgres' }
)
foreach ($w in $watch) {
    $procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like ($w.Stem + '*') })
    $count = $procs.Count
    $mb = 0
    if ($count -gt 0) { $mb = [math]::Round((($procs | Measure-Object WorkingSet64 -Sum).Sum) / 1MB, 0) }
    Write-Host ("  {0,-22} : {1,3} proc {2,8} MB" -f $w.Label, $count, $mb)
}

Write-Host "`n[Odoo language server]" -ForegroundColor Yellow
$ls = @(Get-Process -Name 'odoo_ls_server' -ErrorAction SilentlyContinue)
if ($ls.Count -eq 0) {
    Write-Host '  not running'
} else {
    $over = @($ls | Where-Object { [math]::Round($_.WorkingSet64 / 1MB, 0) -ge $LsMaxMB })
    foreach ($p in $ls) {
        $mb = [math]::Round($p.WorkingSet64 / 1MB, 0)
        $flag = if ($mb -ge $LsMaxMB) { '  <-- over limit' } else { '' }
        Write-Host ("  pid {0,-6} : {1,6} MB{2}" -f $p.Id, $mb, $flag)
    }
    if ($over.Count -gt 0) {
        if ($Reclaim) {
            foreach ($p in $over) {
                Write-Host ("  stopping pid {0} ..." -f $p.Id) -ForegroundColor DarkYellow
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            }
            Write-Host ("  Stopped {0} instance(s); the Odoo extension respawns it on demand." -f $over.Count) -ForegroundColor Green
        } else {
            Write-Host ("  Over {0} MB - re-run with -Reclaim to stop it." -f $LsMaxMB) -ForegroundColor DarkGray
        }
    }
}

Write-Host "`n[Odoo stack ports]" -ForegroundColor Yellow
$ports = @(
    @{ Port = 8069; Label = 'Odoo HTTP' }
    @{ Port = 8072; Label = 'Odoo longpolling' }
    @{ Port = 5432; Label = 'PostgreSQL' }
)
foreach ($p in $ports) {
    $c = Get-NetTCPConnection -State Listen -LocalPort $p.Port -ErrorAction SilentlyContinue
    if ($c) {
        $state = "LISTENING (pid $($c[0].OwningProcess))"
    } else {
        $state = 'not listening'
    }
    Write-Host ("  {0,-20} :{1} -> {2}" -f $p.Label, $p.Port, $state)
}

Write-Host "`n[Top 5 memory consumers]" -ForegroundColor Yellow
Get-Process -ErrorAction SilentlyContinue |
    Sort-Object WorkingSet64 -Descending |
    Select-Object -First 5 |
    ForEach-Object { Write-Host ("  {0,-24} {1,8} MB" -f $_.ProcessName, [math]::Round($_.WorkingSet64 / 1MB, 0)) }

if ($Clean) {
    Write-Host "`n[Cleanup: stale PowerShell hosts]" -ForegroundColor Yellow
    $mine = Get-AncestorIds -StartPid $PID
    $cutoff = (Get-Date).AddMinutes(-$StaleMinutes)
    $targets = @(
        Get-CimInstance Win32_Process -Filter "Name = 'pwsh.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.ProcessId -ne $PID -and
                -not $mine.Contains([int]$_.ProcessId) -and
                $_.CreationDate -and $_.CreationDate -lt $cutoff
            }
    )
    if ($targets.Count -eq 0) {
        Write-Host ("  Nothing stale (older than {0} min)." -f $StaleMinutes)
    } else {
        foreach ($t in $targets) {
            Write-Host ("  stopping pid {0}" -f $t.ProcessId) -ForegroundColor DarkYellow
            Stop-Process -Id $t.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Write-Host ("  Stopped {0} stale host(s)." -f $targets.Count) -ForegroundColor Green
    }
} elseif (-not $Reclaim) {
    Write-Host "`n(Read-only. Use -Clean for stale shell hosts, -Reclaim for an oversized Odoo LS.)" -ForegroundColor DarkGray
}

Write-Host "`n$sep" -ForegroundColor Cyan
