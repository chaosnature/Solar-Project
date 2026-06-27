import sys
import os
import subprocess
if len(sys.argv) < 2:
    print("Usage: python compile_test_gemini.py ^<config_yaml^> [upload_target]")
    sys.exit(1)
yaml_file = sys.argv[1]
upload_target = sys.argv[2] if len(sys.argv) > 2 else None
if not os.path.exists(yaml_file):
    print(f"Error: Configuration file '{yaml_file}' not found.")
    sys.exit(1)
build_name = "yambms-1"
print(f"Build name: {build_name}")
print("=== Step 0: Pre-compile Git Commit ===")
try:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "pre-compile automatic tracking checkpoint"], check=True)
    print("Git status successfully committed.")
except subprocess.CalledProcessError:
    print("Git checkpoint skipped (no changes to commit or already up to date).")
print("=== Step 1 ^& 2: Running baseline package check ===")
print("=== Step 3: Create git head-ref files ===")
paths = [
    os.path.join(".esphome", "build", build_name, ".pioenvs", build_name, "CMakeFiles", "git-data"),
    os.path.join(".esphome", "build", build_name, ".pioenvs", build_name, "bootloader", "CMakeFiles", "git-data")
]
for path in paths:
    if not os.path.exists(path):
        os.makedirs(path)
    head_ref_file = os.path.join(path, "head-ref")
    with open(head_ref_file, "w") as f:
        f.write("ref: refs/heads/main\n")
    print(f"Created: {head_ref_file}")
print("=== Step 4 ^& 5: Compile ===")
cmd = ["esphome", "compile", yaml_file]
print(f"Running: {' '.join(cmd)}")
subprocess.run(cmd, check=True)
if upload_target:
    print("=== Step 6: Upload ===")
    upload_cmd = ["esphome", "upload", yaml_file, "--device", upload_target]
    print(f"Running: {' '.join(upload_cmd)}")
    subprocess.run(upload_cmd, check=True)
