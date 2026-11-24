# ============================================================
#  STEP-HARDEN : Odoo 19 Security Hardening (Run as Administrator)
# ============================================================
#  วัตถุประสงค์:
#   1. ล็อกพอร์ต 8070 (Odoo ตรง)      -> เข้าจาก LAN เท่านั้น
#   2. ล็อกพอร์ต 80  (nginx reverse)  -> รับเฉพาะ Cloudflare IP + LAN
#      (คงการเข้าใช้ของออฟฟิศ เพราะออฟฟิศเข้ามาทาง pdev-erp.auto-info.com -> Cloudflare)
#   3. [-CleanNginxRules] ลบ firewall rule "nginx" ที่เปิดทุกพอร์ตบน Public (กว้างเกินไป)
#   4. [-LockPostgres]    ล็อก PostgreSQL ให้ฟังเฉพาะ localhost
#   5. [-FullScan]        ตรวจ Defender Exclusion + สแกนเต็ม
#
#  Usage (PowerShell as Administrator):
#    ดูตัวอย่างก่อน (ไม่แก้อะไร):  & "C:\odoo-dev\odoo19\STEP-HARDEN-Firewall-Odoo19.ps1"
#    ลงมือแก้ firewall:           & "C:\odoo-dev\odoo19\STEP-HARDEN-Firewall-Odoo19.ps1" -Apply
#    ครบทุกอย่าง:                 & "C:\odoo-dev\odoo19\STEP-HARDEN-Firewall-Odoo19.ps1" -Apply -CleanNginxRules -LockPostgres -FullScan
#
#  หมายเหตุ: ไม่แตะ Cloudflare (ทำใน Dashboard) และไม่แตะ key/secret ใด ๆ
# ============================================================

[CmdletBinding()]
param(
    # ถ้าไม่ใส่ -Apply = โหมดดูตัวอย่าง (dry-run) เท่านั้น
    [switch]$Apply,

    # ลบ rule ชื่อ "nginx" ที่เปิดทุกพอร์ตบน Public profile
    [switch]$CleanNginxRules,

    # ล็อก PostgreSQL listen_addresses = 'localhost' แล้ว restart service (มี downtime สั้น ๆ)
    [switch]$LockPostgres,

    # ตรวจ Defender Exclusion แล้วสั่ง Full Scan
    [switch]$FullScan,

    # subnet ของ LAN ออฟฟิศ (แก้ได้ตามจริง)
    [string[]]$LanSubnets = @("172.20.0.0/22", "10.99.99.0/24"),

    [string]$Prt8070Rule = "Odoo 19 Port 8070",
    [string]$Prt80Rule   = "Odoo19-Nginx-HTTP-80"
)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

function Say($msg, $color = "Gray") { Write-Host $msg -ForegroundColor $color }
function Head($msg) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
}

Head "Odoo 19 Security Hardening"
Say ("Mode : " + $(if ($Apply) { "APPLY (แก้จริง)" } else { "PREVIEW (ดูตัวอย่างเท่านั้น)" })) $(if ($Apply) { "Yellow" } else { "Green" })

# --- 0. ต้องเป็น Administrator ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Say "[ERROR] ต้องรัน PowerShell แบบ Administrator" "Red"
    exit 1
}
Say "[OK] Running as Administrator" "Green"

# --- 1. ดึง Cloudflare IP ranges (สด) ---
Head "1) Cloudflare IP ranges"
$cfV4 = @("173.245.48.0/20","103.21.244.0/22","103.22.200.0/22","103.31.4.0/22","141.101.64.0/18",
          "108.162.192.0/18","190.93.240.0/20","188.114.96.0/20","197.234.240.0/22","198.41.128.0/17",
          "162.158.0.0/15","104.16.0.0/13","104.24.0.0/14","172.64.0.0/13","131.0.72.0/22")
$cfV6 = @("2400:cb00::/32","2606:4700::/32","2803:f800::/32","2405:b500::/32","2405:8100::/32","2a06:98c0::/29","2c0f:f248::/32")
try {
    $live4 = (Invoke-WebRequest -Uri "https://www.cloudflare.com/ips-v4" -UseBasicParsing -TimeoutSec 10).Content -split "\r?\n" | Where-Object { $_.Trim() }
    if ($live4.Count -gt 0) { $cfV4 = $live4.Trim() }
    Say "[OK] ดึง CF IPv4 สดจาก cloudflare.com สำเร็จ ($($cfV4.Count) ranges)" "Green"
} catch {
    Say "[WARN] ต่อ cloudflare.com ไม่ได้ -> ใช้ค่า CF IPv4 ที่ฝังไว้ ($($cfV4.Count) ranges)" "Yellow"
}
try {
    $live6 = (Invoke-WebRequest -Uri "https://www.cloudflare.com/ips-v6" -UseBasicParsing -TimeoutSec 10).Content -split "\r?\n" | Where-Object { $_.Trim() }
    if ($live6.Count -gt 0) { $cfV6 = $live6.Trim() }
    Say "[OK] ดึง CF IPv6 สดสำเร็จ ($($cfV6.Count) ranges)" "Green"
} catch {
    Say "[WARN] ต่อ cloudflare.com ไม่ได้ -> ใช้ค่า CF IPv6 ที่ฝังไว้" "Yellow"
}
$allow80  = @($cfV4) + @($cfV6) + @($LanSubnets)
$allow8070 = @($LanSubnets) + @("127.0.0.1")

# --- 2. แสดงสถานะปัจจุบัน ---
Head "2) สถานะปัจจุบัน (ก่อนแก้)"
function Show-Rule($name) {
    $r = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
    if (-not $r) { Say ("  {0,-24} : <ไม่พบ rule>" -f $name) "Red"; return }
    foreach ($one in $r) {
        $pf = $one | Get-NetFirewallPortFilter
        $af = $one | Get-NetFirewallAddressFilter
        Say ("  {0,-24} : Enabled={1} Action={2} Profile={3} Port={4} Remote={5}" -f $one.DisplayName, $one.Enabled, $one.Action, $one.Profile, $pf.LocalPort, (($af.RemoteAddress | Select-Object -First 3) -join ','))
    }
}
Show-Rule $Prt8070Rule
Show-Rule $Prt80Rule
$nginxRules = Get-NetFirewallRule -DisplayName "nginx" -ErrorAction SilentlyContinue
Say ("  {0,-24} : พบ {1} rule (เปิดทุกพอร์ต/Public)" -f "nginx", ($nginxRules | Measure-Object).Count) $(if ($nginxRules) { "Yellow" } else { "Gray" })

# --- 3. แผนที่จะทำ ---
Head "3) แผนการแก้ไข"
Say "  [8070] Remote -> $($allow8070 -join ', ')" "Cyan"
Say "  [80  ] Remote -> Cloudflare ($($cfV4.Count)+$($cfV6.Count) ranges) + LAN ($($LanSubnets -join ', '))" "Cyan"
if ($CleanNginxRules) { Say "  [nginx] ลบ rule ที่เปิดทุกพอร์ตบน Public" "Cyan" }
if ($LockPostgres)    { Say "  [postgres] listen_addresses = 'localhost' + restart (downtime สั้น ๆ)" "Yellow" }
if ($FullScan)        { Say "  [defender] ตรวจ exclusion + Full Scan (ใช้เวลานาน)" "Yellow" }

if (-not $Apply) {
    Head "PREVIEW เท่านั้น"
    Say "  ยังไม่ได้แก้อะไร -> ใส่ -Apply เพื่อลงมือจริง" "Green"
    Say "  ตัวอย่าง: & `"$PSCommandPath`" -Apply" "Green"
    return
}

# --- 4. APPLY : firewall ---
Head "4) ลงมือแก้ firewall"
if (Get-NetFirewallRule -DisplayName $Prt8070Rule -ErrorAction SilentlyContinue) {
    Set-NetFirewallRule -DisplayName $Prt8070Rule -RemoteAddress $allow8070 -Profile Any
    Say "[OK] ล็อก 8070 -> LAN เท่านั้น" "Green"
} else {
    Say "[SKIP] ไม่พบ rule 8070" "Yellow"
}

if (Get-NetFirewallRule -DisplayName $Prt80Rule -ErrorAction SilentlyContinue) {
    Set-NetFirewallRule -DisplayName $Prt80Rule -RemoteAddress $allow80 -Profile Any
    Say "[OK] ล็อก 80 -> Cloudflare IP + LAN" "Green"
} else {
    Say "[SKIP] ไม่พบ rule 80" "Yellow"
}

if ($CleanNginxRules) {
    $n = Get-NetFirewallRule -DisplayName "nginx" -ErrorAction SilentlyContinue
    if ($n) {
        $n | Remove-NetFirewallRule
        Say "[OK] ลบ rule `"nginx`" ที่เปิดกว้าง ($($n.Count) รายการ)" "Green"
    } else {
        Say "[SKIP] ไม่มี rule `"nginx`"" "Yellow"
    }
}

# --- 5. APPLY : PostgreSQL ---
if ($LockPostgres) {
    Head "5) ล็อก PostgreSQL -> localhost"
    $pgConf = "C:\Program Files\PostgreSQL\16\data\postgresql.conf"
    $svc    = "postgresql-x64-16"
    if (Test-Path $pgConf) {
        $backup = "$pgConf.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
        Copy-Item $pgConf $backup
        Say "  สำรองไฟล์เดิม -> $backup" "Gray"
        $raw = Get-Content $pgConf -Raw
        $new = [regex]::Replace($raw, "(?m)^\s*#?\s*listen_addresses\s*=.*$", "listen_addresses = 'localhost'")
        Set-Content -Path $pgConf -Value $new -NoNewline
        Say "[OK] แก้ listen_addresses = 'localhost'" "Green"
        Restart-Service $svc
        Say "[OK] restart service $svc แล้ว" "Green"
    } else {
        Say "[SKIP] ไม่พบ $pgConf" "Yellow"
    }
    Say "  [เตือน] ถ้ามี Odoo/โปรแกรมจากเครื่องอื่นต่อ PostgreSQL เครื่องนี้ จะต่อไม่ได้" "Yellow"
}

# --- 6. APPLY : Defender ---
if ($FullScan) {
    Head "6) Defender"
    $p = Get-MpPreference
    Say "  ExclusionPath      : $($p.ExclusionPath -join ', ')"
    Say "  ExclusionProcess   : $($p.ExclusionProcess -join ', ')"
    Say "  ExclusionExtension : $($p.ExclusionExtension -join ', ')"
    Say "  [หมายเหตุ] ถ้าไม่รู้จักรายการข้างบน ให้สงสัยไว้ก่อน" "Yellow"
    Say "  กำลังเริ่ม Full Scan (ใช้เวลานาน)..." "Yellow"
    Start-MpScan -ScanType FullScan
    Say "[OK] สแกนเต็มเสร็จสิ้น" "Green"
}

# --- 7. ตรวจผลหลังแก้ ---
Head "7) ตรวจผลหลังแก้"
Show-Rule $Prt8070Rule
Show-Rule $Prt80Rule
$lb = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" }
Say ""
Say "  IP เครื่องนี้: $(($lb.IPAddress) -join ', ')" "Cyan"
Say "  ทดสอบในเครื่อง : http://localhost:8070/web" "Cyan"
Say "  ทดสอบผ่านเว็บ  : https://pdev-erp.auto-info.com" "Cyan"
Say ""
Say "เสร็จสิ้น (ถ้าออฟฟิศเข้าไม่ได้ ให้รันสคริปต์นี้ซ้ำโดยแก้ -LanSubnets ให้ตรงจริง)" "Green"
