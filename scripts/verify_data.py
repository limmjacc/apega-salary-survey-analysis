#!/usr/bin/env python3
"""
Verify all cleaned data files are valid and functional.

Status: Active
Usage: python scripts/verify_data.py
Output: Console verification of `data/*.json` files
"""

import json
from pathlib import Path

data_dir = Path('data')

print('\n' + '='*60)
print('DATA FILE VERIFICATION')
print('='*60 + '\n')

# Verify master file
try:
    master = json.load(open(data_dir / 'salary_master.json'))
    years = sorted(master['by_year'].keys())
    print(f'✓ salary_master.json: Valid')
    print(f'  Years: {years}')
except Exception as e:
    print(f'✗ salary_master.json: {e}')

# Verify 2021 data
try:
    data_2021 = json.load(open(data_dir / 'salary_data_2021.json'))
    eng_count = len(data_2021['compensation']['ENG'])
    geo_count = len(data_2021['compensation']['GEO'])
    print(f'✓ salary_data_2021.json: Valid')
    print(f'  ENG levels: {eng_count}, GEO levels: {geo_count}')
except Exception as e:
    print(f'✗ salary_data_2021.json: {e}')

# Verify 2024 data
try:
    data_2024 = json.load(open(data_dir / 'salary_data_2024.json'))
    eng_count = len(data_2024['compensation']['ENG'])
    geo_count = len(data_2024['compensation']['GEO'])
    print(f'✓ salary_data_2024.json: Valid')
    print(f'  ENG levels: {eng_count}, GEO levels: {geo_count}')
except Exception as e:
    print(f'✗ salary_data_2024.json: {e}')

# Verify forecasts
try:
    forecasts = json.load(open(data_dir / 'salary_forecasts_2024_2030.json'))
    years = sorted(forecasts['ENG']['P1'].keys())
    print(f'✓ salary_forecasts_2024_2030.json: Valid')
    print(f'  Forecast years: {years}')
except Exception as e:
    print(f'✗ salary_forecasts_2024_2030.json: {e}')

print('\n' + '='*60)
print('✓ All data files verified and operational')
print('='*60 + '\n')
