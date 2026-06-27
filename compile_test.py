import sys
import os
import subprocess

if len(sys.argv) < 2:
    print("Usage: python compile_test.py <config_yaml> [upload_target]")
    sys.exit(1)

yaml_file = sys.argv[1]
upload_target = sys.argv[2] if len(sys.argv) > 2 else None

build_name = "yambms-1"

print(f"Build name: {build_name}")

print("=== Step 1 & 2: Running baseline package check ===")
# Note: The PowerShell direct patch handles the rebulk limits in the cache.

print("=== Step 3: Create git head-ref files ===")
paths = [
    f".esphome\\build\\{build_name}\\.pioenvs\\{build_name}\\CMakeFiles\\git-data",
    f".esphome\\build\\{build_name}\\.pioenvs\\{build_name}\\bootloader\\CMakeFiles\\git-data"
]

for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, "head-ref"), "w") as f:
        f.write("ref: refs/heads/main\n")
    print(f"Created: {path}\\head-ref")

print("=== Step 4 & 5: Compile and Upload ===")
cmd = ["esphome", "compile", yaml_file]
print(f"Running: {' '.join(cmd)}")
subprocess.run(cmd)

if upload_target:
    upload_cmd = ["esphome", "upload", yaml_file, "--device", upload_target]
    print(f"Running: {' '.join(upload_cmd)}")
    subprocess.run(upload_cmd)
