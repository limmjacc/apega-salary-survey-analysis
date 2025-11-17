#!/usr/bin/env python3
"""
Generate quick reference tables for salary forecasts - markdown export.

Status: Active
Usage: python scripts/generate_reference_tables.py
Output: Markdown table printed to stdout
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'

# Load forecasts
with open(DATA_DIR / 'salary_forecasts_2024_2030.json', 'r') as f:
    forecasts = json.load(f)

# Load historical
with open(DATA_DIR / 'salary_master.json', 'r') as f:
    historical = json.load(f)

def print_table(title, levels, forecasts, historical):
    print(f"\n## {title}\n")
    
    # Header
    header = "| Level | 2023 Base | 2024 | 2025 | 2026 | 2027 | 2028 | 2029 | 2030 |"
    separator = "|-------|-----------|------|------|------|------|------|------|------|"
    print(header)
    print(separator)
    
    # Rows
    for level in levels:
        row = f"| {level}"
        
        # 2023 base
        if level in historical['by_year']['2023']['ENG']:
            base_2023 = historical['by_year']['2023']['ENG'][level]
            row += f" | ${base_2023:,}"
        else:
            row += " | -"
        
        # Forecasts
        if level in forecasts['ENG']:
            for year in [2024, 2025, 2026, 2027, 2028, 2029, 2030]:
                salary = forecasts['ENG'][level][str(year)]
                row += f" | ${salary:,}"
        else:
            row += " | - | - | - | - | - | - | -"
        
        row += " |"
        print(row)

print("# APEGA Salary Forecast Reference (2024-2030)")
print("**All figures in CAD (median base salary)**")

print_table("Engineering (ENG) - Professional Levels", 
           ['P1', 'P2', 'P3', 'P4', 'P5'], 
           forecasts, historical)

print_table("Engineering (ENG) - Management Levels", 
           ['M1', 'M2', 'M3', 'M4', 'M5'], 
           forecasts, historical)

print("\n## Growth Summary (2023 to 2030)\n")
print("| Level | 2023 Base | 2030 Forecast | Dollar Growth | % Growth |")
print("|-------|-----------|---------------|---------------|----------|")

for level in ['P1', 'P2', 'P3', 'P4', 'P5', 'M1', 'M2', 'M3', 'M4', 'M5']:
    if level in historical['by_year']['2023']['ENG']:
        base_2023 = historical['by_year']['2023']['ENG'][level]
        if level in forecasts['ENG']:
            forecast_2030 = forecasts['ENG'][level]['2030']
            dollar_growth = forecast_2030 - base_2023
            pct_growth = ((forecast_2030 - base_2023) / base_2023) * 100
            print(f"| {level} | ${base_2023:,} | ${forecast_2030:,} | ${dollar_growth:,} | {pct_growth:+.1f}% |")

print("\n---")
print("\n**Notes:**")
print("- All forecasts use combined linear + polynomial regression model")
print("- 2021 data excluded (PDF corruption); 2024 based on Scribd images")
print("- M5 forecasts highly uncertain (only 1-3 historical data points/year)")
print("- Geoscience (GEO) data insufficient for independent forecasting")
print("\nSee `data/ANALYSIS_REPORT.md` for full methodology and caveats.")
