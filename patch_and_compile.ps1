# patch_and_compile.ps1
# Run this BEFORE compiling to fix all known cache issues
# Usage: .\patch_and_compile.ps1 YamBMS_STRING1_TEST.yaml
# Usage: .\patch_and_compile.ps1 YamBMS_STRING2_TEST.yaml

param(
    [Parameter(Mandatory=$true)]
    [string]$YamlFile
)

Write-Host "=== Step 1: Fix all refs from main to 1.5.8 in YAML ===" -ForegroundColor Cyan
(Get-Content $YamlFile) -replace '    ref: main', '    ref: 1.5.8' | Set-Content $YamlFile
Write-Host "Done"

Write-Host "=== Step 2: Patch ALL cached bms_sensors_JK_BLE_standard.yaml files ===" -ForegroundColor Cyan
$files = Get-ChildItem -Recurse -Path ".esphome\packages" -Filter "bms_sensors_JK_BLE_standard.yaml" -ErrorAction SilentlyContinue
foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw
    $patched = $content -replace 'github://syssi/esphome-jk-bms@main', 'github://syssi/esphome-jk-bms@2.5.0'
    $patched | Set-Content $file.FullName
    Write-Host "Patched: $($file.FullName)"
}
if ($files.Count -eq 0) { Write-Host "No cached files found yet (will be needed after first compile attempt)" }

Write-Host "=== Step 3: Git commit to fix CMake head-ref error ===" -ForegroundColor Cyan
git add .
git commit -m "pre-compile patch" 2>&1 | Out-Null
Write-Host "Done"

Write-Host "=== Step 4: Compile ===" -ForegroundColor Cyan
python compile_test.py $YamlFile

# Patch total_battery_capacity number entity to add id in both cache folders
Write-Host "=== Step 2b: Patch total_battery_capacity id ===" -ForegroundColor Cyan
Get-ChildItem -Recurse -Path ".esphome\packages" -Filter "bms_sensors_JK_BLE_standard.yaml" -ErrorAction SilentlyContinue | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -notmatch 'bms\$\{bms_id\}_total_capacity_number') {
        $content = $content -replace '    total_battery_capacity:\r?\n      name:', "    total_battery_capacity:`r`n      id: bms`${bms_id}_total_capacity_number`r`n      name:"
        $content = $content -replace '    total_battery_capacity:\r?\n      device_id:', "    total_battery_capacity:`r`n      id: bms`${bms_id}_total_capacity_number`r`n      device_id:"
        $content | Set-Content $_.FullName
        Write-Host "Patched total_capacity_number id: $($_.FullName)"
    }
}
