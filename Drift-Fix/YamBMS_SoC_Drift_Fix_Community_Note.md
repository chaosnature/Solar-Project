# YamBMS SoC Coulomb Drift Fix
**Developed:** June 2026 | YamBMS v1.5.8+ | ESPHome 2025.11.0 | M5Stack AtomS3-Lite

---

## Problem

JK-BMS coulomb counters drift over time, causing SoC to show incorrect values (e.g. 85% when the battery is actually full). The BMS needs an anchor event to recalibrate its coulomb counter back to 100%.

---

## Root Cause

The JK-BMS recalibrates its SoC when the `total_battery_capacity` number entity is changed. YamBMS does not trigger this automatically, so drift accumulates over charge/discharge cycles.

---

## Solution

Add inline globals and two interval lambdas directly to your main YAML. These monitor voltage, current, and SoC. When all three indicate a full charge held for 30 seconds, the fix toggles the capacity number to force recalibration — then restores it 10 seconds later. No `delay()` is used, keeping the main loop unblocked.

---

## Implementation

### Step 1: Add id to total_battery_capacity in cached package

In `.esphome/packages/<hash>/packages/bms/bms_sensors_JK_BLE_standard.yaml`, find the `total_battery_capacity:` number entry and add an `id:`:

```yaml
    total_battery_capacity:
      id: bms${bms_id}_total_capacity_number   # <-- add this line
      name: "${name} ${bms_name} total battery capacity"
```

> **Note:** This patch must be reapplied after each cache refresh, or set `refresh: 365d` in your packages to prevent re-downloading.

---

### Step 2: Add to your main YAML

Append the following to the end of your main YAML file (adjust voltage thresholds for your system):

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

interval:
  - interval: 5s
    then:
      - lambda: |-
          // BMS1
          if (id(bms1_online_status).state) {
            float v = id(bms1_total_voltage).state;
            float i = id(bms1_current).state;
            float s = id(bms1_state_of_charge).state;
            if (!isnan(v) && !isnan(i) && !isnan(s)) {
              bool full = (v >= 56.4f) && (i <= 2.0f) && (s >= 98.0f);
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
                if (id(bms1_soc_anchored) && v < 55.0f) {
                  id(bms1_soc_anchored) = false;
                  ESP_LOGI("soc_fix", "BMS1: anchor reset V=%.2f", v);
                }
              }
            }
          }
          // BMS2
          if (id(bms2_online_status).state) {
            float v = id(bms2_total_voltage).state;
            float i = id(bms2_current).state;
            float s = id(bms2_state_of_charge).state;
            if (!isnan(v) && !isnan(i) && !isnan(s)) {
              bool full = (v >= 56.4f) && (i <= 2.0f) && (s >= 98.0f);
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
                if (id(bms2_soc_anchored) && v < 55.0f) {
                  id(bms2_soc_anchored) = false;
                  ESP_LOGI("soc_fix", "BMS2: anchor reset V=%.2f", v);
                }
              }
            }
          }

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
```

---

## Trigger Conditions (all three must hold for 30 seconds)

| Condition | Value |
|---|---|
| Battery voltage | >= 56.4V (just below float) |
| Charge current | <= 2A (nearly stopped) |
| State of Charge | >= 98% |

**Reset condition:** voltage drops below 55.0V (new discharge cycle detected)

---

## Voltage Reference (adjust for your system)

| Setting | Value |
|---|---|
| Bulk voltage | 57.0V |
| Float voltage | 56.6V |
| Rebulk voltage | ~51.8V |
| Drift fix trigger | 56.4V |
| Drift fix reset | 55.0V |

---

## Log Output

When triggered:
```
[I][soc_fix]: BMS1: anchor triggered V=56.72 I=1.20 SoC=99%
[I][soc_fix]: BMS1: capacity restored to 95Ah
```

When reset (new discharge cycle):
```
[I][soc_fix]: BMS1: anchor reset V=54.20
```

---

## Important Notes

- Adjust voltage thresholds to match **your** bulk/float voltages
- This fix is **per-BMS** — each BMS has its own globals and counter
- Tested on YamBMS v1.5.8 and v1.6.0 with ESPHome 2025.11.0 on M5Stack AtomS3-Lite
- The fix is **non-destructive** — toggles capacity by 1Ah temporarily only
- Do **not** use `delay()` inside ESPHome interval lambdas — it blocks the main loop and causes watchdog panics. This implementation uses two separate intervals instead.
- Single-BMS setups: remove the BMS2 globals and BMS2 block from the lambda
