# Isolated install test for od19_sc_core (private DB + port). Writes kept inside allowed workspace.
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$Root    = 'C:\odoo-dev\odoo19'
$Python  = Join-Path $Root 'venv19\Scripts\python.exe'
$OdooBin = Join-Path $Root 'odoo-bin'
$Conf    = Join-Path $Root 'odoo.conf'
$DataDir = Join-Path $Root 'data'
$DB      = $env:SC_TEST_DB
if (-not $DB) { $DB = 'odoo19_t_trae_sc3' }
$Module  = $env:SC_MODULE
if (-not $Module) { $Module = 'od19_sc_core' }
$Port    = 8090
$Log     = Join-Path $Root '_sc_install_test.log'

$addons = @(
    'C:\odoo-dev\od19_sc\custom_addons',
    "$Root\addons",
    "$Root\odoo\addons"
) -join ','

$args = @(
    $OdooBin, '-c', $Conf,
    '-d', $DB,
    '--db-filter', "^$DB$",
    '--data-dir', $DataDir,
    '--http-port', $Port,
    '--addons-path', $addons,
    '-i', $Module,
    '--stop-after-init',
    '--logfile', $Log,
    '--no-http'
)
Write-Host ("> " + $Python + " " + ($args -join ' '))
& $Python @args
$code = $LASTEXITCODE
Write-Host ("exit code = " + $code)
exit $code
