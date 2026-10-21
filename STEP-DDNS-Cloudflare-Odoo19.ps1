# STEP-DDNS : Cloudflare DDNS script for Odoo 19 PDEV
# อัปเดต A record pdev-erp.auto-info.com เมื่อ public IP เปลี่ยน
# เรียกจาก STEP-3-Start-Odoo19.ps1 อัตโนมัติ และจาก Task Scheduler
#   (\Cloudflare DDNS - Odoo19 ทุก 5 นาที)
# Usage: .\STEP-DDNS-Cloudflare-Odoo19.ps1

# Token อ่านจาก environment variable เท่านั้น (ห้าม hardcode ลงใน repo)
# ตั้งค่าแบบถาวรระดับ user:
#   [Environment]::SetEnvironmentVariable('CLOUDFLARE_API_TOKEN','<your-token>','User')
$CloudflareToken = $env:CLOUDFLARE_API_TOKEN
if ([string]::IsNullOrWhiteSpace($CloudflareToken)) {
    Write-Error "CLOUDFLARE_API_TOKEN is not set. ตั้งค่า environment variable ก่อนรันสคริปต์ (ห้าม hardcode token ใน repo)."
    exit 1
}
$ZoneId = "f39fe4f71f19460344be4088c3223398"
$RecordName = "pdev-erp.auto-info.com"
$LogFile = "C:\odoo-dev\odoo19\ddns_update.log"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $msg" | Out-File -FilePath $LogFile -Append -Encoding UTF8
}

try {
    # Get current public IP
    $currentIP = (Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 15).ip
    Write-Log "Current public IP: $currentIP"

    # Get existing DNS record from Cloudflare
    $headers = @{
        "Authorization" = "Bearer $CloudflareToken"
        "Content-Type" = "application/json"
    }
    $listUrl = "https://api.cloudflare.com/client/v4/zones/$ZoneId/dns_records?name=$RecordName&type=A"
    $record = (Invoke-RestMethod -Uri $listUrl -Headers $headers -Method Get).result[0]

    if (-not $record) {
        Write-Log "ERROR: DNS record $RecordName not found"
        exit 1
    }

    $recordId = $record.id
    $cloudflareIP = $record.content

    if ($currentIP -eq $cloudflareIP) {
        Write-Log "IP unchanged ($currentIP). No update needed."
        exit 0
    }

    # IP changed - update the record
    Write-Log "IP changed: $cloudflareIP -> $currentIP. Updating..."
    $updateBody = @{
        type = "A"
        name = $RecordName
        content = $currentIP
        ttl = 1
        proxied = $true
    } | ConvertTo-Json

    $updateUrl = "https://api.cloudflare.com/client/v4/zones/$ZoneId/dns_records/$recordId"
    $result = Invoke-RestMethod -Uri $updateUrl -Headers $headers -Method Put -Body $updateBody

    if ($result.success) {
        Write-Log "SUCCESS: DNS record updated to $currentIP"
    } else {
        Write-Log "FAILED: $($result.errors -join ', ')"
    }
} catch {
    Write-Log "ERROR: $($_.Exception.Message)"
}
