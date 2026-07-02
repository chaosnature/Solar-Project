# YamBMS SoC Coulomb Drift Fix
**Developed:** June/July 2026 | YamBMS v1.5.8+ | ESPHome 2025.11.0 | M5Stack AtomS3-Lite

---

## Problem

JK-BMS coulomb counters drift over time, causing SoC to show incorrect values. The BMS needs anchor events to recalibrate its coulomb counter.

---

## Root Cause

The JK-BMS recalibrates its SoC from voltage when the `total_battery_capacity` number entity is changed. YamBMS does not trigger this automatically, so drift accumulates over charge/discharge cycles.

> **Note:** When the capacity is toggled, the JK-BMS recalculates SoC based on current cell voltages — it does NOT simply reset to 100%.

---

## Bugs Found and Fixed (July 2026)

### Bug 1 — Wrong voltage sensor in lambda
The lambda was reading `bms1_total_voltage` (raw JK-BMS BLE sensor) but thresholds were calibrated against `yambms1_total_voltage` (YamBMS-processed value shown in HA). These differ by ~0.14V, causing the top anchor to never fire.

**Fix:** Change `id(bms1_total_voltage).state` to `id(yambms1_total_voltage).state` in all anchor lambdas.

### Bug 2 — Bottom anchor was silently resetting the top anchor counter
The bottom anchor interval contained `if (v > 50.0f) { id(bms1_soc_anchor_counter) = 0; }` which fired every 5 seconds during normal operation, wiping the top anchor counter before it could reach 6.

**Fix:** Remove those lines entirely from the bottom anchor.

---

## Solution

Three anchor points per cycle:

| Anchor | Trigger Conditions | Why |
|---|---|---|
| **Top** | V >= 55.0V (YamBMS), I <= 3A, SoC >= 60%, sustained 30s | Calibrates at top of charge |
| **Mid** | Avg cell 3.68-3.72V, within +-10A | Catches mid-cycle drift |
| **Bottom** | V <= 48.0V, I >= -2A, SoC <= 5% | Calibrates at bottom of charge |

> **Important:** Adjust the top anchor voltage to match YOUR inverter charge ceiling. Always check `yambms1_total_voltage` in HA — NOT the raw BMS sensor which reads ~0.14V lower.

---

## Implementation

### Step 1: Add id to total_battery_capacity in cached package

In `.esphome/packages/<hash>/packages/bms/bms_sensors_JK_BLE_standard.yaml`:

```yaml
    total_battery_capacity:
      id: bms${bms_id}_total_capacity_number
      name: "${name} ${bms_name} total battery capacity"
```

Set `refresh: 365d` in your packages section to prevent ESPHome overwriting this patch.

---

### Step 2: Add globals

```yaml
globals:
  - id: bms1_soc_anchor_counter
    type: int
    restore_value: false
    initial_value: '0'
  - id: bms1_soc_anchored
    type: bool
    restore_value: false
    initial_value: 'false'
  - id: bms1_restore_pending
    type: bool
    restore_value: false
    initial_value: 'false'
  - id: bms1_mid_anchored
    type: bool
    restore_value: false
    initial_value: 'false'
  - id: bms2_soc_anchor_counter
    type: int
    restore_value: false
    initial_value: '0'
  - id: bms2_soc_anchored
    type: bool
    restore_value: false
    initial_value: 'false'
  - id: bms2_restore_pending
    type: bool
    restore_value: false
    initial_value: 'false'
  - id: bms2_mid_anchored
    type: bool
    restore_value: false
    initial_value: 'false'
```

---

### Step 3: Add interval lambdas

```yaml
interval:
  # TOP ANCHOR
  # KEY FIX 1: use yambms1_total_voltage not bms1_total_voltage
  # KEY FIX 2: removed bottom anchor counter reset that sabotaged this
  - interval: 5s
    then:
      - lambda: |-
          if (id(bms1_online_status).state) {
            float v = id(yambms1_total_voltage).state;
            float i = id(bms1_current).state;
            float s = id(bms1_state_of_charge).state;
            if (!isnan(v) && !isnan(i) && !isnan(s)) {
              bool full = (v >= 55.0f) && (i <= 3.0f) && (s >= 60.0f);
              if (full) {
                id(bms1_soc_anchor_counter)++;
                if (id(bms1_soc_anchor_counter) >= 6 && !id(bms1_soc_anchored)) {
                  auto call = id(bms1_total_capacity_number).make_call();
                  call.set_value(94.0f);
                  call.perform();
                  id(bms1_soc_anchored) = true;
                  id(bms1_restore_pending) = true;
                  ESP_LOGI("soc_fix", "BMS1: anchor triggered V=%.2f I=%.2f SoC=%.0f%%", v, i, s);
                }
              } else {
                id(bms1_soc_anchor_counter) = 0;
                if (id(bms1_soc_anchored) && v < 53.0f) {
                  id(bms1_soc_anchored) = false;
                  ESP_LOGI("soc_fix", "BMS1: anchor reset V=%.2f", v);
                }
              }
            }
          }
          if (id(bms2_online_status).state) {
            float v = id(yambms1_total_voltage).state;
            float i = id(bms2_current).state;
            float s = id(bms2_state_of_charge).state;
            if (!isnan(v) && !isnan(i) && !isnan(s)) {
              bool full = (v >= 55.0f) && (i <= 3.0f) && (s >= 60.0f);
              if (full) {
                id(bms2_soc_anchor_counter)++;
                if (id(bms2_soc_anchor_counter) >= 6 && !id(bms2_soc_anchored)) {
                  auto call = id(bms2_total_capacity_number).make_call();
                  call.set_value(94.0f);
                  call.perform();
                  id(bms2_soc_anchored) = true;
                  id(bms2_restore_pending) = true;
                  ESP_LOGI("soc_fix", "BMS2: anchor triggered V=%.2f I=%.2f SoC=%.0f%%", v, i, s);
                }
              } else {
                id(bms2_soc_anchor_counter) = 0;
                if (id(bms2_soc_anchored) && v < 53.0f) {
                  id(bms2_soc_anchored) = false;
                  ESP_LOGI("soc_fix", "BMS2: anchor reset V=%.2f", v);
                }
              }
            }
          }

  # RESTORE
  - interval: 10s
    then:
      - lambda: |-
          if (id(bms1_restore_pending)) {
            auto call = id(bms1_total_capacity_number).make_call();
            call.set_value(95.0f);
            call.perform();
            id(bms1_restore_pending) = false;
            ESP_LOGI("soc_fix", "BMS1: capacity restored to 95Ah");
          }
          if (id(bms2_restore_pending)) {
            auto call = id(bms2_total_capacity_number).make_call();
            call.set_value(95.0f);
            call.perform();
            id(bms2_restore_pending) = false;
            ESP_LOGI("soc_fix", "BMS2: capacity restored to 95Ah");
          }

  # BOTTOM ANCHOR
  # KEY FIX: removed "if (v > 50.0f) { counter = 0; }" that sabotaged top anchor
  - interval: 5s
    then:
      - lambda: |-
          if (id(bms1_online_status).state) {
            float v = id(yambms1_total_voltage).state;
            float i = id(bms1_current).state;
            float s = id(bms1_state_of_charge).state;
            if (!isnan(v) && !isnan(i) && !isnan(s)) {
              bool near_empty = (v <= 48.0f) && (i >= -2.0f) && (s <= 5.0f);
              if (near_empty && !id(bms1_restore_pending)) {
                auto call = id(bms1_total_capacity_number).make_call();
                call.set_value(94.0f);
                call.perform();
                id(bms1_restore_pending) = true;
                ESP_LOGI("soc_fix", "BMS1: BOTTOM anchor triggered V=%.2f I=%.2f SoC=%.0f%%", v, i, s);
              }
            }
          }
          if (id(bms2_online_status).state) {
            float v = id(yambms1_total_voltage).state;
            float i = id(bms2_current).state;
            float s = id(bms2_state_of_charge).state;
            if (!isnan(v) && !isnan(i) && !isnan(s)) {
              bool near_empty = (v <= 48.0f) && (i >= -2.0f) && (s <= 5.0f);
              if (near_empty && !id(bms2_restore_pending)) {
                auto call = id(bms2_total_capacity_number).make_call();
                call.set_value(94.0f);
                call.perform();
                id(bms2_restore_pending) = true;
                ESP_LOGI("soc_fix", "BMS2: BOTTOM anchor triggered V=%.2f I=%.2f SoC=%.0f%%", v, i, s);
              }
            }
          }

  # MID ANCHOR
  - interval: 5s
    then:
      - lambda: |-
          if (id(bms1_online_status).state) {
            float avg = id(bms1_average_cell_voltage).state;
            float i   = id(bms1_current).state;
            if (!isnan(avg) && !isnan(i)) {
              bool mid_rest = (avg >= 3.68f) && (avg <= 3.72f) && (i >= -10.0f) && (i <= 10.0f);
              if (mid_rest && !id(bms1_restore_pending) && !id(bms1_mid_anchored)) {
                auto call = id(bms1_total_capacity_number).make_call();
                call.set_value(94.0f);
                call.perform();
                id(bms1_restore_pending) = true;
                id(bms1_mid_anchored) = true;
                ESP_LOGI("soc_fix", "BMS1: MID anchor triggered avg=%.3fV I=%.2fA", avg, i);
              }
              if (avg < 3.60f || avg > 3.80f) {
                id(bms1_mid_anchored) = false;
              }
            }
          }
          if (id(bms2_online_status).state) {
            float avg = id(bms2_average_cell_voltage).state;
            float i   = id(bms2_current).state;
            if (!isnan(avg) && !isnan(i)) {
              bool mid_rest = (avg >= 3.68f) && (avg <= 3.72f) && (i >= -10.0f) && (i <= 10.0f);
              if (mid_rest && !id(bms2_restore_pending) && !id(bms2_mid_anchored)) {
                auto call = id(bms2_total_capacity_number).make_call();
                call.set_value(94.0f);
                call.perform();
                id(bms2_restore_pending) = true;
                id(bms2_mid_anchored) = true;
                ESP_LOGI("soc_fix", "BMS2: MID anchor triggered avg=%.3fV I=%.2fA", avg, i);
              }
              if (avg < 3.60f || avg > 3.80f) {
                id(bms2_mid_anchored) = false;
              }
            }
          }
```

---

## Important Notes

- **Always use `yambms1_total_voltage`** in lambdas — NOT `bms1_total_voltage`
- Adjust voltage thresholds to match **your** system's actual charge ceiling
- Tested on YamBMS v1.5.8 with ESPHome 2025.11.0 on M5Stack AtomS3-Lite
- Do **not** use `delay()` inside ESPHome interval lambdas — causes watchdog panics
- Full working YAML: https://github.com/chaosnature/Solar-Project
