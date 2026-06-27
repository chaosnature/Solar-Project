#!/usr/bin/env python3
"""
fix_ha_dashboard_46.py
Fixes HA lovelace dashboard entity IDs for TEST HA at 192.168.0.46
Entities on .46 have NO 'kitchen_' prefix.
Run on Pi: sudo python3 fix_ha_dashboard_46.py

Usage:
  sudo python3 fix_ha_dashboard_46.py --dry-run   # preview changes only
  sudo python3 fix_ha_dashboard_46.py             # apply changes and restart HA
"""

import json, re, os, sys, subprocess, shutil
from datetime import datetime

LOVELACE = '/usr/share/hassio/homeassistant/.storage/lovelace'

# Entity ID replacements: (old_prefix, new_prefix)
# Order matters — more specific first
REPLACEMENTS = [
    # String-1: old entity names -> new prefix (NO kitchen_ on .46)
    ('sensor.jk_bms_1_',                    'sensor.yambms_1_string_1_jk_bms_1_'),
    ('sensor.jk_bms_2_',                    'sensor.yambms_1_string_1_jk_bms_2_'),
    ('binary_sensor.jk_bms_1_',             'binary_sensor.yambms_1_string_1_jk_bms_1_'),
    ('binary_sensor.jk_bms_2_',             'binary_sensor.yambms_1_string_1_jk_bms_2_'),
    ('binary_sensor.yambms_1_board_online_status', 'binary_sensor.yambms_1_string_1_esp32_online_status'),
    ('binary_sensor.canbus_1_status',        'binary_sensor.yambms_1_string_1_canbus_1_status'),
    ('number.jk_bms_1_',                    'number.yambms_1_string_1_jk_bms_1_'),
    ('number.jk_bms_2_',                    'number.yambms_1_string_1_jk_bms_2_'),
    ('switch.jk_bms_1_',                    'switch.yambms_1_string_1_jk_bms_1_'),
    ('switch.jk_bms_2_',                    'switch.yambms_1_string_1_jk_bms_2_'),
    ('sensor.yambms_1_board_internal_temperature', 'sensor.yambms_1_string_1_esp32_internal_temperature'),
    ('number.yambms_1_string_1_yambms_1_',  'number.yambms_1_string_1_yambms_1_'),
    ('sensor.yambms_1_string_1_yambms_1_',  'sensor.yambms_1_string_1_yambms_1_'),
    ('switch.yambms_1_string_1_yambms_1_',  'switch.yambms_1_string_1_yambms_1_'),
]

dry_run = '--dry-run' in sys.argv

# Backup
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
backup = LOVELACE + f'.backup-{ts}'
shutil.copy2(LOVELACE, backup)
print(f'Backup saved: {backup}')

with open(LOVELACE) as f:
    content = f.read()

total = 0
for old, new in REPLACEMENTS:
    count = content.count(old)
    if count:
        print(f'  {count}x: {old[:55]} -> {new[:55]}')
        content = content.replace(old, new)
        total += count

print(f'\nTotal replacements: {total}')

if dry_run:
    print('DRY RUN — no changes written.')
else:
    with open(LOVELACE, 'w') as f:
        f.write(content)
    print('Written to lovelace')
    print('Restarting HA...')
    subprocess.run(['ha', 'core', 'restart'], check=False)
    print('Done — wait 2-3 minutes then refresh dashboard.')
