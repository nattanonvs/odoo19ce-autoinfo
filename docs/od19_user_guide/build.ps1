# build.ps1 — assemble the full Odoo 19 AutoInfo user handbook
# Reads shell_head.html + parts/*.html (sorted) + shell_foot.html
# Generates: docs/od19_full_user_guide_20261119.html
# Run:  pwsh -File build.ps1
# NOTE: keep this script ASCII-only (Thai content lives in the part files).

$ErrorActionPreference = 'Stop'

$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$partsDir = Join-Path $here 'parts'
$outFile  = Join-Path (Split-Path -Parent $here) 'od19_full_user_guide_20261119.html'

$head = Get-Content (Join-Path $here 'shell_head.html') -Raw -Encoding UTF8
$foot = Get-Content (Join-Path $here 'shell_foot.html') -Raw -Encoding UTF8

if (-not (Test-Path $partsDir)) { throw "parts folder not found: $partsDir" }
$partFiles = Get-ChildItem $partsDir -Filter '*.html' | Sort-Object Name
if ($partFiles.Count -eq 0) { throw "no part files in $partsDir" }

$partsHtml = ''
$tocItems  = ''
$modCount  = 0
$partCount = 0
$idx       = 0

foreach ($pf in $partFiles) {
    $raw = Get-Content $pf.FullName -Raw -Encoding UTF8
    $idx++
    $partCount++

    # ---- parse meta block:  <!--Part  id=..  title=..  icon=..  sub=..  --> ----
    $meta = @{}
    if ($raw -match '(?s)<!--\s*Part(.*?)-->') {
        foreach ($line in ($Matches[1] -split "`n")) {
            $line = $line.Trim()
            if ($line -match '^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+)$') {
                $meta[$Matches[1].ToLower()] = $Matches[2].Trim()
            }
        }
    }
    $partId = if ($meta['id'])    { $meta['id'] }    else { "part$idx" }
    $ptitle = if ($meta['title']) { $meta['title'] } else { "Part $idx" }
    $picon  = if ($meta['icon'])  { $meta['icon'] }  else { '&#128196;' }
    $psum   = $meta['sub']

    # ---- collect modules: <h3 class="mod" ... id="..." ...>...</h3> ----
    $modLinks = ''
    $rx = [regex]'(?s)<h3 class="mod"[^>]*\bid="([^"]+)"[^>]*>(.*?)</h3>'
    foreach ($m in $rx.Matches($raw)) {
        $mid  = $m.Groups[1].Value
        $mtxt = ($m.Groups[2].Value -replace '<[^>]+>', '' -replace '\s+', ' ').Trim()
        $modCount++
        $modLinks += '<li><a href="#' + $mid + '">' + $mtxt + '</a></li>'
    }

    # ---- master TOC entry ----
    $tocItems += '<li class="tocpart"><a href="#' + $partId + '"><span class="tocico">' + $picon + '</span>' + $ptitle + '</a>'
    if ($psum)     { $tocItems += '<div class="tocsub">' + $psum + '</div>' }
    if ($modLinks) { $tocItems += '<ul class="tocmods">' + $modLinks + '</ul>' }
    $tocItems += '</li>'

    $partsHtml += "`n" + $raw + "`n"
}

$masterToc = '<ol class="lvl1">' + $tocItems + '</ol>'
$buildDate = (Get-Date).ToString('yyyy-MM-dd')

$out = $head
$out = $out.Replace('{{MASTER_TOC}}', $masterToc)
$out = $out.Replace('{{PART_COUNT}}', [string]$partCount)
$out = $out.Replace('{{MOD_COUNT}}',  [string]$modCount)
$out = $out + $partsHtml + "`n" + $foot
$out = $out.Replace('{{BUILD_DATE}}', $buildDate)

# write UTF-8 (with BOM so browsers/Windows editors detect Thai correctly)
$utf8Bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($outFile, $out, $utf8Bom)

Write-Host ("Built: {0}" -f $outFile)
Write-Host ("Parts: {0}   Modules: {1}" -f $partCount, $modCount)
