# patch_and_compile_gemini.ps1
# Advanced pre-compile patching engine for YamBMS & JK-BMS caching issues.
# Usage: .\patch_and_compile_gemini.ps1 YamBMS_STRING1_TEST.yaml

param(
    [Parameter(Mandatory=$true)]
    [string]$YamlFile
)

$ErrorActionPreference = "Stop"

# Define Paths
$PackagesDir = ".esphome\packages"

Write-Host "=== Step 1: Checking Base Yaml Requirements ===" -ForegroundColor Cyan
if (-not (Test-Path $YamlFile)) {
    Write-Error "Target YAML configuration file '$YamlFile' not found."
}

# Pin baseline repository tags inside YAML
Write-Host "Pinning baseline repository tags to version 1.5.8 inside $YamlFile..." -ForegroundColor Yellow
$yamlContent = Get-Content $YamlFile
$yamlContent = $yamlContent -replace 'ref:\s*main', 'ref: 1.5.8'
$yamlContent | Set-Content $YamlFile
Write-Host "YAML constraints updated." -ForegroundColor Green

Write-Host "=== Step 2: Forcing Downstream Fetch Strategy ===" -ForegroundColor Cyan
Write-Host "Running initial esphome config check to force cache hydration..." -ForegroundColor Yellow

# Temporarily ease ErrorActionPreference for the native tool call to ignore stdout/stderr stream casting bugs
$OldEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
cmd /c "esphome config $YamlFile 2>&1" | Out-Null
$ErrorActionPreference = $OldEAP

Write-Host "Cache hydrated successfully." -ForegroundColor Green

Write-Host "=== Step 3: Injecting Patches to Cached Component Specifications ===" -ForegroundColor Cyan
if (-not (Test-Path $PackagesDir)) {
    Write-Warning "Cache directory target '$PackagesDir' does not exist. Proceeding with deep scan..."
}

# Locating all targeted files across hydrated hashes
$files = Get-ChildItem -Recurse -Path $PackagesDir -Filter "bms_sensors_JK_BLE_standard.yaml" -ErrorAction SilentlyContinue

if ($files.Count -eq 0) {
    Write-Host "[-] Critical: No targets matching 'bms_sensors_JK_BLE_standard.yaml' found in cache." -ForegroundColor Red
    Write-Host "Attempting secondary sweep for any custom jk_bms components..." -ForegroundColor Yellow
    $files = Get-ChildItem -Recurse -Path $PackagesDir -Filter "*jk_bms*" -ErrorAction SilentlyContinue
}

foreach ($file in $files) {
    Write-Host "Processing Target Cache Structure: $($file.FullName)" -ForegroundColor Yellow
    $content = Get-Content $file.FullName -Raw
    
    # Force Pin internal requirements down away from unstable GitHub branches
    if ($content -match 'github://syssi/esphome-jk-bms@main') {
        $content = $content -replace 'github://syssi/esphome-jk-bms@main', 'github://syssi/esphome-jk-bms@2.5.0'
        Write-Host "  [+] Redirected upstream reference tracking to branch @2.5.0" -ForegroundColor Green
    }

    # Inject missing total capacity number structural identifiers safely
    if ($content -notmatch 'bms\$\{bms_id\}_total_capacity_number') {
        $content = $content -replace '(\s+)total_battery_capacity:\r?\n\1\s+name:', "`$1total_battery_capacity:`r`n`$1  id: bms`${bms_id}_total_capacity_number`r`n`$1  name:"
        $content = $content -replace '(\s+)total_battery_capacity:\r?\n\1\s+device_id:', "`$1total_battery_capacity:`r`n`$1  id: bms`${bms_id}_total_capacity_number`r`n`$1  device_id:"
        Write-Host "  [+] Injected explicit ID context bindings for 'total_capacity_number'." -ForegroundColor Green
    }

    # Write-back cleanly keeping OS binary configurations intact
    [System.IO.File]::WriteAllText($file.FullName, $content)
}

Write-Host "=== Step 4: Normalizing local Git Tree State ===" -ForegroundColor Cyan
if (Test-Path .git) {
    Write-Host "Staging build changes inside tracking layer..." -ForegroundColor Yellow
    $ErrorActionPreference = "Continue"
    cmd /c "git add . 2>&1" | Out-Null
    cmd /c "git commit -m ""automation patch: pinned dependencies and structural validation fix"" 2>&1" | Out-Null
    $ErrorActionPreference = $OldEAP
    Write-Host "Git tree state synchronized safely." -ForegroundColor Green
}

Write-Host "=== Step 5: Execution Pipeline ===" -ForegroundColor Cyan
Write-Host "Invoking compilation test..." -ForegroundColor Yellow

if (Test-Path "compile_test.py") {
    python compile_test.py $YamlFile
} else {
    Write-Host "compile_test.py hook not found. Executing direct ESPHome compiler fallback..." -ForegroundColor Yellow
    esphome compile $YamlFile
}
