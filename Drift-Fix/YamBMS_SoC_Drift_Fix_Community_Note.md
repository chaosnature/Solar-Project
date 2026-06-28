# YamBMS SoC Coulomb Drift Fix
**Developed:** June 2026 | YamBMS v1.5.8+ | ESPHome 2025.11.0 | M5Stack AtomS3-Lite

---

## Problem

JK-BMS coulomb counters drift over time, causing SoC to show incorrect values (e.g. 85% when the battery is actually full, or 15% when it's nearly empty). The BMS needs anchor events to recalibrate its coulomb counter.

---

## Root Cause

The JK-BMS recalibrates its SoC from voltage when the `total_battery_capacity` number entity is changed. YamBMS does not trigger this automatically, so drift accumulates over charge/discharge cycles.

> **Note:** When the capacity is toggled, the JK-BMS recalculates SoC based on current cell voltages — it does NOT simply reset to 100%. This means anchoring at any point in the cycle gives an accurate recalibration based on actual voltage.

---

## Solution

Two anchor points per cycle — top and bottom — matching how professional BMS systems work:

| Anchor | Trigger Conditions | Why |
|---|---|---|
| **Top** | V >= 56.4V, I <= 2A, SoC >= 98% | Steep curve = accurate voltage-to-SoC mapping |
| **Bottom** | V <= 48.0V, I >= -2A, SoC <= 5% | Steep curve = accurate voltage-to-SoC mapping |

Mid-cycle anchoring (20-80% SoC) is avoided because the LFP discharge curve is very flat there — voltage-to-SoC mapping is unreliable.

---

## Implementation

### Step 1: Add id to total_battery_capacity in cached package

In `.esphome/packages/<hash>/packages/bms/bms_sensors_JK_BLE_standard.yaml`, find the `total_battery_capacity:` number entry and add an `id:`:

```yaml
    total_battery_capacity:
      id: bms${bms_id}_total_capacity_number   # <-- add this line
      name: "${name} ${bms_name} total battery capacity"
```

> **Important:** Set `refresh: 365d` in your packages section to prevent ESPHome re-downloading and overwriting this patch on every compile.

---

### Step 2: Add to your main YAML

Append the following to the end of your main YAML file. Adjust voltage thresholds to match your system's bulk/float voltages.

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
  # TOP anchor - triggers when battery is genuinely full
  - interval: 5s
    then:
      - lambda: |-
          // BMS1 top anchor
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
                  ESP_LOGI("soc_fix", "BMS1: TOP anchor triggered V=%.2f I=%.2f SoC=%.0f%%", v, i, s);
                }
              } else {
                id(bms1_soc_anchor_counter) = 0;
                if (id(bms1_soc_anchored) && v < 55.0f) {
                  id(bms1_soc_anchored) = false;
                  ESP_LOGI("soc_fix", "BMS1: top anchor reset V=%.2f", v);
                }
              }
            }
          }
          // BMS2 top anchor
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
                  ESP_LOGI("soc_fix", "BMS2: TOP anchor triggered V=%.2f I=%.2f SoC=%.0f%%", v, i, s);
                }
              } else {
                id(bms2_soc_anchor_counter) = 0;
                if (id(bms2_soc_anchored) && v < 55.0f) {
                  id(bms2_soc_anchored) = false;
                  ESP_LOGI("soc_fix", "BMS2: top anchor reset V=%.2f", v);
                }
              }
            }
          }

  # BOTTOM anchor - triggers when battery is genuinely empty
  - interval: 5s
    then:
      - lambda: |-
          // BMS1 bottom anchor
          if (id(bms1_online_status).state) {
            float v = id(bms1_total_voltage).state;
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
              if (v > 50.0f) {
                id(bms1_soc_anchor_counter) = 0;
              }
            }
          }
          // BMS2 bottom anchor
          if (id(bms2_online_status).state) {
            float v = id(bms2_total_voltage).state;
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
              if (v > 50.0f) {
                id(bms2_soc_anchor_counter) = 0;
              }
            }
          }

  # Restore capacity 10 seconds after any anchor trigger
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

## Voltage Reference (adjust for your system)

| Setting | Value |
|---|---|
| Bulk voltage | 57.0V |
| Float voltage | 56.6V |
| Rebulk voltage | ~51.8V |
| Top anchor trigger | 56.4V (just below float) |
| Top anchor reset | 55.0V |
| Bottom anchor trigger | 48.0V (near empty) |
| Bottom anchor reset | 50.0V |

---

## Log Output

Top anchor:
```
[I][soc_fix]: BMS1: TOP anchor triggered V=56.72 I=1.20 SoC=99%
[I][soc_fix]: BMS1: capacity restored to 95Ah
[I][soc_fix]: BMS1: top anchor reset V=54.20
```

Bottom anchor:
```
[I][soc_fix]: BMS1: BOTTOM anchor triggered V=47.80 I=-1.50 SoC=4%
[I][soc_fix]: BMS1: capacity restored to 95Ah
```

---

## Important Notes

- Adjust all voltage thresholds to match **your** system's bulk/float voltages
- This fix is **per-BMS** — each BMS has its own globals and counter
- Tested on YamBMS v1.5.8 and v1.6.0 with ESPHome 2025.11.0 on M5Stack AtomS3-Lite
- The fix is **non-destructive** — toggles capacity by 1Ah temporarily only
- Do **not** use `delay()` inside ESPHome interval lambdas — it blocks the main loop and causes watchdog panics. This implementation uses two separate intervals instead
- **Why not mid-cycle?** LFP cells have a very flat voltage curve between 20-80% SoC — voltage-to-SoC mapping is unreliable at those levels. Top and bottom anchors use the steep parts of the curve where voltage accurately reflects SoC
- Single-BMS setups: remove the BMS2 globals and BMS2 blocks from each lambda
