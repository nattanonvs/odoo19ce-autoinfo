<#
.SYNOPSIS
    Update/install Odoo 19 CE custom modules on Windows Server.

.EXAMPLE
    # Update every module already installed (default)
    powershell -ExecutionPolicy Bypass -File .\update_odoo19_ce_modules.ps1

.EXAMPLE
    # Install new modules, then update the existing ones
    powershell -ExecutionPolicy Bypass -File .\update_odoo19_ce_modules.ps1 -Install od19_accounting_operational_closure,od19_accounting_reporting

.EXAMPLE
    # Skip git pull/submodule, use another database
    powershell -ExecutionPolicy Bypass -File .\update_odoo19_ce_modules.ps1 -SkipGit -Database odoo19_acc_test
#>
param(
    [string]$Database = "odoo19_pdev",
    [string]$Branch = "19.0",
    [string[]]$Install = @(),
    [string[]]$Update = @(
        "od19_contacts_partner_roles",
        "od19_sales_project_context",
        "od19_sales_contract_core",
        "od19_sales_billing_evidence",
        "od19_sales_reporting",
        "od19_sales_oca_bridge_workflow",
        "od19_purchase_procurement_core",
        "od19_inventory_execution_control",
        "od19_inventory_audit_count",
        "od19_inventory_reporting"
    ),
    [switch]$SkipGit
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = Join-Path $Root "venv19\Scripts\python.exe"
$OdooBin = Join-Path $Root "odoo-bin"
$Config = Join-Path $Root "odoo.conf"

function Invoke-Step([string]$Title, [scriptblock]$Action) {
    Write-Host "`n=== $Title ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Title failed (exit code $LASTEXITCODE)" }
}

Set-Location $Root

foreach ($path in @($Python, $OdooBin, $Config)) {
    if (-not (Test-Path $path)) { throw "Not found: $path" }
}

# Modules to install must exist in custom_addons (i.e. already merged into the branch)
foreach ($module in $Install) {
    if (-not (Test-Path (Join-Path $Root "custom_addons\$module\__manifest__.py"))) {
        throw "Module '$module' not found in custom_addons. Merge it into '$Branch' before installing."
    }
}

if (-not $SkipGit) {
    Invoke-Step "git pull origin $Branch" { git pull origin $Branch }
    Invoke-Step "git submodule update" { git submodule update --init --recursive }
}

if ($Install.Count -gt 0) {
    $installList = $Install -join ","
    Invoke-Step "Install: $installList" {
        & $Python $OdooBin -c $Config -d $Database -i $installList --stop-after-init
    }
}

# Do not update modules that were just installed
$toUpdate = $Update | Where-Object { $Install -notcontains $_ }
if ($toUpdate.Count -gt 0) {
    $updateList = $toUpdate -join ","
    Invoke-Step "Update: $updateList" {
        & $Python $OdooBin -c $Config -d $Database -u $updateList --stop-after-init
    }
}

Write-Host "`nDone. Database: $Database" -ForegroundColor Green
