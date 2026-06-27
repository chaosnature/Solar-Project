# Fix 1: correct the drift fix comment
f1 = r"packages\bms\bms_soc_drift_fix_JK_BLE.yaml"
with open(f1, "r", encoding="utf-8") as fh:
    c = fh.read()
c = c.replace("// voltage >= 54.8V, current <= 2A, SoC >= 98%",
              "// voltage >= 56.4V, current <= 2A, SoC >= 98%")
with open(f1, "w", encoding="utf-8") as fh:
    fh.write(c)
print("Fix 1: drift fix comment corrected")

# Fix 2: remove web server password
f2 = r"packages\yambms\yambms_web_server.yaml"
with open(f2, "r", encoding="utf-8") as fh:
    c = fh.read()
c = c.replace("  auth:\n    username: !secret web_server_username\n    password: !secret web_server_password",
              "  #auth:\n  #  username: !secret web_server_username\n  #  password: !secret web_server_password")
with open(f2, "w", encoding="utf-8") as fh:
    fh.write(c)
print("Fix 2: web server auth commented out")
