#!/usr/bin/env python3
"""
Solar Battery Monitor — ChaosNature
Run from Pi:      python3 solar_monitor.py
Run from Windows: python solar_monitor.py
"""

import urllib.request
import json
import os
import time

# ── CONFIG ──────────────────────────────────────────────────────────────────
HA_URL   = "http://192.168.1.13:8123"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ZTgyN2FlNjFjMWU0NWJjODFiOTZkZjQxOTFjZDgzZCIsImlhdCI6MTc4NTY3Mzg1NCwiZXhwIjoyMTAxMDMzODU0fQ.SfqxHrXiN1Sns9JT7firs9KborZ3ue8W-APa2vwe3ao"   # paste your HA long-lived token here
# ────────────────────────────────────────────────────────────────────────────

ENTITIES = {
    # String 1
    "bms1_soc":    "sensor.kitchen_yambms_1_string_1_jk_bms_1_state_of_charge",
    "bms2_soc":    "sensor.kitchen_yambms_1_string_1_jk_bms_2_state_of_charge",
    "bms1_volt":   "sensor.kitchen_yambms_1_string_1_jk_bms_1_total_voltage",
    "bms2_volt":   "sensor.kitchen_yambms_1_string_1_jk_bms_2_total_voltage",
    "bms1_curr":   "sensor.kitchen_yambms_1_string_1_jk_bms_1_current",
    "bms2_curr":   "sensor.kitchen_yambms_1_string_1_jk_bms_2_current",
    "bms1_cell":   "sensor.kitchen_yambms_1_string_1_jk_bms_1_average_cell_voltage",
    "bms2_cell":   "sensor.kitchen_yambms_1_string_1_jk_bms_2_average_cell_voltage",
    "bms1_online": "binary_sensor.kitchen_yambms_1_string_1_jk_bms_1_online_status",
    "bms2_online": "binary_sensor.kitchen_yambms_1_string_1_jk_bms_2_online_status",
    "yam1_ccl":    "sensor.kitchen_yambms_1_string_1_yambms_1_requested_charge_current",
    "yam1_cvl":    "sensor.kitchen_yambms_1_string_1_yambms_1_requested_charge_voltage",
    "yam1_volt":   "sensor.kitchen_yambms_1_string_1_yambms_1_total_voltage",
    # String 2
    "bms3_soc":    "sensor.kitchen_yambms_2_string_2_jk_bms_3_state_of_charge",
    "bms4_soc":    "sensor.kitchen_yambms_2_string_2_jk_bms_4_state_of_charge",
    "bms3_volt":   "sensor.kitchen_yambms_2_string_2_jk_bms_3_total_voltage",
    "bms4_volt":   "sensor.kitchen_yambms_2_string_2_jk_bms_4_total_voltage",
    "bms3_curr":   "sensor.kitchen_yambms_2_string_2_jk_bms_3_current",
    "bms4_curr":   "sensor.kitchen_yambms_2_string_2_jk_bms_4_current",
    "bms3_cell":   "sensor.kitchen_yambms_2_string_2_jk_bms_3_average_cell_voltage",
    "bms4_cell":   "sensor.kitchen_yambms_2_string_2_jk_bms_4_average_cell_voltage",
    "bms3_online": "binary_sensor.kitchen_yambms_2_string_2_jk_bms_3_online_status",
    "bms4_online": "binary_sensor.kitchen_yambms_2_string_2_jk_bms_4_online_status",
    "yam2_ccl":    "sensor.kitchen_yambms_2_string_2_yambms_2_requested_charge_current",
    "yam2_cvl":    "sensor.kitchen_yambms_2_string_2_yambms_2_requested_charge_voltage",
    "yam2_volt":   "sensor.kitchen_yambms_2_string_2_yambms_2_total_voltage",
}

def get_state(entity_id):
    url = f"{HA_URL}/api/states/{entity_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {HA_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())["state"]
    except Exception as e:
        return "ERR"

def fetch_all():
    return {key: get_state(entity) for key, entity in ENTITIES.items()}

def soc_bar(val, width=20):
    try:
        pct = float(val)
    except:
        pct = 0
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if pct > 60:   color = "\033[92m"  # green
    elif pct > 25: color = "\033[93m"  # yellow
    else:          color = "\033[91m"  # red
    return f"{color}[{bar}]\033[0m {pct:.0f}%"

def curr_label(val):
    try:
        c = float(val)
    except:
        return "?"
    if c > 0.5:    return f"\033[92m+{c:.2f}A ▲ charging\033[0m"
    elif c < -0.5: return f"\033[93m{c:.2f}A ▼ discharging\033[0m"
    else:          return f"\033[90m{c:.2f}A  idle\033[0m"

def online_dot(val):
    return "\033[92m●\033[0m" if val == "on" else "\033[91m●\033[0m"

def warn(msg):
    return f"\033[91m  ⚠  {msg}\033[0m"

def header(text):
    print(f"\n\033[1;34m{'═'*60}\033[0m")
    print(f"\033[1;37m  {text}\033[0m")
    print(f"\033[1;34m{'═'*60}\033[0m")

def bms_block(label, soc, volt, curr, cell, online):
    dot = online_dot(online)
    print(f"\n  {dot} \033[1m{label}\033[0m")
    print(f"     SoC:     {soc_bar(soc)}")
    try:
        print(f"     Voltage: {float(volt):.2f}V   Avg cell: {float(cell):.3f}V")
    except:
        print(f"     Voltage: {volt}V   Avg cell: {cell}V")
    print(f"     Current: {curr_label(curr)}")

def check_alerts(d):
    alerts = []
    # Voltage gaps
    try:
        vg1 = abs(float(d["bms1_volt"]) - float(d["bms2_volt"]))
        if vg1 > 1.0:
            alerts.append(f"STRING-1 VOLTAGE GAP: {vg1:.2f}V — batteries fighting! Equalise before reconnecting")
    except: pass
    try:
        vg2 = abs(float(d["bms3_volt"]) - float(d["bms4_volt"]))
        if vg2 > 1.0:
            alerts.append(f"STRING-2 VOLTAGE GAP: {vg2:.2f}V — batteries fighting! Equalise before reconnecting")
    except: pass
    # SoC gaps
    try:
        sg1 = abs(float(d["bms1_soc"]) - float(d["bms2_soc"]))
        if sg1 > 15:
            alerts.append(f"STRING-1 SOC GAP: {sg1:.0f}% — drift detected, check fuse on lower unit")
    except: pass
    try:
        sg2 = abs(float(d["bms3_soc"]) - float(d["bms4_soc"]))
        if sg2 > 15:
            alerts.append(f"STRING-2 SOC GAP: {sg2:.0f}% — drift detected, check fuse on lower unit")
    except: pass
    # Cross-current
    try:
        c1, c2 = float(d["bms1_curr"]), float(d["bms2_curr"])
        if (c1 > 2 and c2 < -2) or (c1 < -2 and c2 > 2):
            alerts.append(f"STRING-1 CROSS-CURRENT: BMS1={c1:.1f}A BMS2={c2:.1f}A — one charging the other!")
    except: pass
    try:
        c3, c4 = float(d["bms3_curr"]), float(d["bms4_curr"])
        if (c3 > 2 and c4 < -2) or (c3 < -2 and c4 > 2):
            alerts.append(f"STRING-2 CROSS-CURRENT: BMS3={c3:.1f}A BMS4={c4:.1f}A — one charging the other!")
    except: pass
    # High current
    for k, label in [("bms1_curr","BMS1"),("bms2_curr","BMS2"),("bms3_curr","BMS3"),("bms4_curr","BMS4")]:
        try:
            if abs(float(d[k])) > 15:
                alerts.append(f"HIGH CURRENT on {label}: {float(d[k]):.1f}A — check inverter limits")
        except: pass
    # Low SoC
    for k, label in [("bms1_soc","BMS1"),("bms2_soc","BMS2"),("bms3_soc","BMS3"),("bms4_soc","BMS4")]:
        try:
            if float(d[k]) <= 5:
                alerts.append(f"LOW BATTERY on {label}: {float(d[k]):.0f}% — critically low!")
        except: pass
    return alerts

def print_report(d):
    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n\033[1;33m⚡ SOLAR BATTERY MONITOR\033[0m  —  {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ── STRING 1 ──
    header("STRING 1 — Kitchen / Solis 3kW")
    try:
        print(f"  YamBMS Pack: {float(d['yam1_volt']):.2f}V  |  CCL: {float(d['yam1_ccl']):.0f}A  |  CVL: {float(d['yam1_cvl']):.1f}V")
    except: pass
    bms_block("JKBMS-1 (Master)", d["bms1_soc"], d["bms1_volt"], d["bms1_curr"], d["bms1_cell"], d["bms1_online"])
    bms_block("JKBMS-2 (Slave)",  d["bms2_soc"], d["bms2_volt"], d["bms2_curr"], d["bms2_cell"], d["bms2_online"])
    try:
        vg = abs(float(d["bms1_volt"]) - float(d["bms2_volt"]))
        sg = abs(float(d["bms1_soc"])  - float(d["bms2_soc"]))
        print(f"\n  Gaps → Voltage: {vg:.2f}V  |  SoC: {sg:.0f}%")
    except: pass

    # ── STRING 2 ──
    header("STRING 2 — Shed / Sofar HYD 3600")
    try:
        print(f"  YamBMS Pack: {float(d['yam2_volt']):.2f}V  |  CCL: {float(d['yam2_ccl']):.0f}A  |  CVL: {float(d['yam2_cvl']):.1f}V")
    except: pass
    bms_block("JKBMS-3 (Master)", d["bms3_soc"], d["bms3_volt"], d["bms3_curr"], d["bms3_cell"], d["bms3_online"])
    bms_block("JKBMS-4 (Slave)",  d["bms4_soc"], d["bms4_volt"], d["bms4_curr"], d["bms4_cell"], d["bms4_online"])
    try:
        vg = abs(float(d["bms3_volt"]) - float(d["bms4_volt"]))
        sg = abs(float(d["bms3_soc"])  - float(d["bms4_soc"]))
        print(f"\n  Gaps → Voltage: {vg:.2f}V  |  SoC: {sg:.0f}%")
    except: pass

    # ── ALERTS ──
    alerts = check_alerts(d)
    if alerts:
        print(f"\n\033[1;31m{'═'*60}")
        print("  🚨 ALERTS")
        print(f"{'═'*60}\033[0m")
        for a in alerts:
            print(warn(a))
    else:
        print(f"\n\033[92m  ✓ All clear — no issues detected\033[0m")

    print(f"\n\033[90m  Press Ctrl+C to exit  |  Auto-refreshes every 15s\033[0m\n")

def main():
    print("Connecting to Home Assistant...")
    while True:
        try:
            d = fetch_all()
            print_report(d)
            time.sleep(15)
        except KeyboardInterrupt:
            print("\n\nExiting. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(15)

if __name__ == "__main__":
    main()
