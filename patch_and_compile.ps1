# patch_and_compile.ps1
# Run this BEFORE compiling to fix all known cache issues
# Usage: .\patch_and_compile.ps1 YamBMS_STRING1_ORIGINAL.yaml

param(
    [Parameter(Mandatory=$true)]
    [string]$YamlFile
)

Write-Host "=== Step 1: Fix all refs from main to 1.5.8 in YAML ===" -ForegroundColor Cyan
(Get-Content $YamlFile -Raw) -replace '    ref: main', '    ref: 1.5.8' | Set-Content $YamlFile
Write-Host "Done"

Write-Host "=== Step 2: Set refresh to 365d to prevent cache overwrite ===" -ForegroundColor Cyan
(Get-Content $YamlFile -Raw) -replace 'refresh: 0s', 'refresh: 365d' | Set-Content $YamlFile
Write-Host "Done"

Write-Host "=== Step 3: Patch ALL cached bms_sensors_JK_BLE_standard.yaml files ===" -ForegroundColor Cyan
$files = Get-ChildItem -Recurse -Path ".esphome\packages" -Filter "bms_sensors_JK_BLE_standard.yaml" -ErrorAction SilentlyContinue
foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    # Pin jk-bms to 2.5.0
    $content = $content -replace 'github://syssi/esphome-jk-bms@main', 'github://syssi/esphome-jk-bms@2.5.0'
    # Add id to total_battery_capacity number entity (e87f1c82 style - has name: next)
    if ($content -notmatch 'bms\$\{bms_id\}_total_capacity_number') {
        $content = $content -replace '    total_battery_capacity:\r?\n      name:', "    total_battery_capacity:`r`n      id: bms`${bms_id}_total_capacity_number`r`n      name:"
        # Add id to total_battery_capacity number entity (a3a4c2d8 style - has device_id: next)
        $content = $content -replace '    total_battery_capacity:\r?\n      device_id:', "    total_battery_capacity:`r`n      id: bms`${bms_id}_total_capacity_number`r`n      device_id:"
        Write-Host "Patched total_capacity_number id: $($file.FullName)"
    }
    [System.IO.File]::WriteAllText($file.FullName, $content)
    Write-Host "Patched: $($file.FullName)"
}
if ($files.Count -eq 0) { Write-Host "No cached files found yet (run once to hydrate cache, then run again)" }

Write-Host "=== Step 4: Git commit to fix CMake head-ref error ===" -ForegroundColor Cyan
git add . 2>&1 | Out-Null
git commit -m "pre-compile patch" 2>&1 | Out-Null
Write-Host "Done"

Write-Host "=== Step 5: Compile ===" -ForegroundColor Cyan
python compile_test.py $YamlFile
