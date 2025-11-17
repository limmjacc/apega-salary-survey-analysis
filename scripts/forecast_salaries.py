#!/usr/bin/env python3
"""
Forecast APEGA salary trends through 2030 using historical data.
Applies linear and polynomial regression to project future compensation.

Status: Active
Usage: python scripts/forecast_salaries.py
Output: `data/salary_forecasts_2024_2030.json` and plots saved to `outputs/`
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
OUTPUT_DIR = ROOT / 'outputs'
OUTPUT_DIR.mkdir(exist_ok=True)

# Plot styling
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10


class SalaryForecaster:
    """Project salary trends using regression models."""
    
    def __init__(self):
        self.master_data = None
        self.years_available = []
        self.forecasts = {}
        self.load_master_data()
    
    def load_master_data(self):
        """Load extracted salary data."""
        master_path = DATA_DIR / 'salary_master.json'
        with open(master_path, 'r') as f:
            self.master_data = json.load(f)
        
        self.years_available = sorted([int(y) for y in self.master_data['by_year'].keys()])
        print(f"Loaded salary data for years: {self.years_available}\n")
    
    def forecast_all(self):
        """Generate forecasts for all career levels and professions."""
        
        print("="*70)
        print("SALARY FORECASTING - 2024-2030")
        print("="*70 + "\n")
        
        # Extract and forecast for each profession and level
        for profession in ['ENG']:  # GEO data is sparse, focus on ENG
            print(f"\n{profession} FORECASTS:\n")
            
            salary_by_level = {}
            for level in ['P1', 'P2', 'P3', 'P4', 'P5', 'M1', 'M2', 'M3', 'M4', 'M5']:
                historical = self._extract_historical(profession, level)
                
                if len(historical) < 2:
                    continue
                
                # Fit models and forecast
                forecast = self._forecast_level(historical, level)
                salary_by_level[level] = forecast
                
                # Display forecast
                last_known = list(historical.values())[-1]
                final_forecast = forecast['2030']
                growth = ((final_forecast - last_known) / last_known) * 100
                print(f"  {level}: ${last_known:,} (2023) -> ${final_forecast:,} (2030) [+{growth:.1f}%]")
            
            # Harmonize group-level growth so levels follow group trends
            salary_by_level = self._harmonize_group_growth(profession, salary_by_level, group_prefix='M')
            self.forecasts[profession] = salary_by_level
        
        self.save_forecasts()
        self.generate_plots()

    def _harmonize_group_growth(self, profession: str, salary_by_level: Dict[str, Dict[str, float]], group_prefix: str = 'M') -> Dict[str, Dict[str, float]]:
        """Adjust forecasts within a career group so each level follows the group's median growth.

        This computes the group's median growth factor (2030 / last_known) for levels
        already in `salary_by_level` and scales any level whose forecasted 2030 is
        below the group's median factor to match the group's trend. This prevents
        isolated declines or flat forecasts that contradict peer-level trends.
        """
        # Collect growth factors for levels in the group
        factors = []
        level_info = {}

        for level, forecast in salary_by_level.items():
            if not level.startswith(group_prefix):
                continue
            # last known historical
            hist = self._extract_historical(profession, level)
            if not hist:
                continue
            years_sorted = sorted(hist.keys())
            last_known = float(hist[years_sorted[-1]])
            # predicted final
            try:
                pred_final = float(forecast.get('2030', last_known))
            except Exception:
                pred_final = last_known

            if last_known > 0:
                factor = pred_final / last_known
                # ignore extreme outliers
                if 0.2 < factor < 10:
                    factors.append(factor)

            level_info[level] = {'last_known': last_known, 'pred_final': pred_final}

        if not factors:
            return salary_by_level

        # Use median growth factor as the group's target
        median_factor = float(np.median(np.array(factors)))

        # Apply adjustments where needed
        for level, info in level_info.items():
            last = info['last_known']
            pred = info['pred_final']
            target_final = last * median_factor

            # If a level's predicted final is below the group's target, scale it up
            if pred < target_final:
                # Linearly interpolate yearly values between last and target_final
                years = list(range(2024, 2031))
                n_years = len(years)
                new_vals = {}
                for idx, y in enumerate(years, start=1):
                    frac = idx / n_years
                    val = last + (target_final - last) * frac
                    new_vals[str(y)] = int(round(val))

                salary_by_level[level] = new_vals

        return salary_by_level
    
    def _extract_historical(self, profession: str, level: str) -> Dict[int, float]:
        """Extract historical salary data for a level."""
        historical = {}
        for year_str, year_data in self.master_data['by_year'].items():
            year = int(year_str)
            prof_data = year_data.get(profession, {})
            if level in prof_data:
                historical[year] = prof_data[level]
        return historical
    
    def _forecast_level(self, historical: Dict[int, float], level: str) -> Dict[str, float]:
        """Fit models and generate forecast for a career level."""
        
        years = np.array(sorted(historical.keys()))
        salaries = np.array([historical[y] for y in years])
        
        # Normalize years for better numerical stability
        years_norm = years - years[0]
        
        # Linear regression
        linear_slope, linear_intercept, r_value_lin, p_value, std_err = \
            stats.linregress(years_norm, salaries)
        
        # Polynomial fit (degree 2)
        poly_coeffs = np.polyfit(years_norm, salaries, 2)
        poly_fit = np.poly1d(poly_coeffs)
        
        # Forecast to 2030
        forecast_data = {}

        # Enforce non-decreasing forecasts relative to the last known historical value
        prev_value = float(salaries[-1])

        # Use polynomial for conservative projection (accounts for potential slowdown)
        for forecast_year in range(2024, 2031):
            year_offset = forecast_year - years[0]
            poly_pred = float(poly_fit(year_offset))
            linear_pred = float(linear_intercept + linear_slope * year_offset)

            # Average both models for robustness
            predicted = (poly_pred + linear_pred) / 2.0

            # Prevent unrealistic year-over-year declines by enforcing monotonicity
            if predicted < prev_value:
                predicted = prev_value

            # Round and store
            rounded = round(predicted)
            forecast_data[str(forecast_year)] = rounded

            # Update previous value for next iteration
            prev_value = float(rounded)

        return forecast_data
    
    def save_forecasts(self):
        """Save forecast data to JSON."""
        output_path = DATA_DIR / 'salary_forecasts_2024_2030.json'
        
        output_data = {
            'metadata': {
                'method': 'Linear + Polynomial (degree 2) regression average',
                'forecast_years': [2024, 2025, 2026, 2027, 2028, 2029, 2030],
                'base_years': self.years_available,
                'note': '2021 data excluded (corruption); GEO data insufficient for forecasting'
            },
            'ENG': self.forecasts.get('ENG', {})
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n* Saved forecasts to: {output_path}")
    
    def generate_plots(self):
        """Create visualization plots of salary trends and forecasts."""
        
        print("\n" + "="*70)
        print("GENERATING PLOTS")
        print("="*70 + "\n")
        
        # Plot 1: All Engineering Levels Combined
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('APEGA Engineering Salary Trends & Forecasts (2020-2030)', fontsize=16, fontweight='bold')
        
        # Plot 1a: Professional levels (P1-P5)
        ax = axes[0, 0]
        self._plot_level_group(ax, 'P', ['P1', 'P2', 'P3', 'P4', 'P5'], 'Professional Levels')
        
        # Plot 1b: Management levels (M1-M5)
        ax = axes[0, 1]
        self._plot_level_group(ax, 'M', ['M1', 'M2', 'M3', 'M4', 'M5'], 'Management Levels')
        
        # Plot 1c: Career progression (P1 to P5)
        ax = axes[1, 0]
        self._plot_career_progression(ax)
        
        # Plot 1d: Salary growth rates by level
        ax = axes[1, 1]
        self._plot_growth_rates(ax)
        
        plt.tight_layout()
        plot1_path = OUTPUT_DIR / 'salary_trends_2020_2030.png'
        plt.savefig(plot1_path, dpi=300, bbox_inches='tight')
        print(f"* Saved: {plot1_path}")
        plt.close()
        
        # Overlay all career levels across years
        self.generate_overlay_plot()
        # ENG-only and GEO-only overlays
        self.generate_profession_overlay('ENG')
        self.generate_profession_overlay('GEO')
        
        # Plot 2: Organization count and diversity trends
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle('APEGA Survey Participation & Demographics (2020-2024)', fontsize=14, fontweight='bold')
        
        # Plot 2a: Org count
        ax = axes[0]
        org_counts = []
        years_org = []
        for year_str, year_data in sorted(self.master_data['by_year'].items()):
            if year_data['org_count']:
                years_org.append(int(year_str))
                org_counts.append(year_data['org_count'])
        
        ax.plot(years_org, org_counts, marker='o', linewidth=2.5, markersize=8, color='#2E86AB', label='Organizations')
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Number of Organizations', fontweight='bold')
        ax.set_title('Participating Organizations')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Plot 2b: Gender split
        ax = axes[1]
        years_gender = []
        eng_pcts = []
        for year_str, year_data in sorted(self.master_data['by_year'].items()):
            if year_data['gender']:
                years_gender.append(int(year_str))
                eng_pcts.append(year_data['gender']['engineers_pct'])
        
        ax.plot(years_gender, eng_pcts, marker='s', linewidth=2.5, markersize=8, color='#A23B72', label='Engineers %')
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Percentage', fontweight='bold')
        ax.set_title('Professional Breakdown (Engineers %)')
        ax.set_ylim([50, 85])
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plot2_path = OUTPUT_DIR / 'participation_trends.png'
        plt.savefig(plot2_path, dpi=300, bbox_inches='tight')
        print(f"* Saved: {plot2_path}")
        plt.close()
        
        # 4-panel visualization: ENG P1-P5, ENG M1-M5, GEO P1-P5, GEO M1-M5
        self.generate_profession_level_panels()
        # Additional separate PNGs requested by user
        self.generate_engineer_P1_P5_by_year()
        self.generate_engineer_M1_M5_by_year()
        self.generate_P1_P5_overlay_by_level()
        self.generate_historical_growth_rates_by_category()
        self.generate_median_and_total_cash_by_level()
    
    def _plot_level_group(self, ax, group: str, levels: List[str], title: str):
        """Plot a group of career levels."""
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(levels)))
        
        for level, color in zip(levels, colors):
            historical = self._extract_historical('ENG', level)
            if not historical:
                continue
            
            hist_years = sorted(historical.keys())
            hist_salaries = [historical[y] for y in hist_years]
            
            # Plot historical
            ax.plot(hist_years, hist_salaries, marker='o', linestyle='-', 
                   linewidth=2, markersize=6, label=level, color=color)
            
            # Plot forecast
            if level in self.forecasts.get('ENG', {}):
                forecast = self.forecasts['ENG'][level]
                forecast_years = [int(y) for y in sorted(forecast.keys())]
                forecast_salaries = [forecast[str(y)] for y in forecast_years]
                
                # Connect last historical to first forecast
                extended_years = hist_years + forecast_years
                extended_salaries = hist_salaries + forecast_salaries
                
                ax.plot(forecast_years, forecast_salaries, marker='o', linestyle='--', 
                       linewidth=2, markersize=6, color=color, alpha=0.6)
                
                # Shade forecast region
                ax.axvspan(2023.5, 2030, alpha=0.1, color='gray')
        
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Median Base Salary ($CAD)', fontweight='bold')
        ax.set_title(title)
        ax.legend(loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    def _plot_career_progression(self, ax):
        """Plot salary progression from entry to senior levels."""
        
        years_to_plot = [2020, 2022, 2023, 2030]  # Include forecast
        
        for year in years_to_plot:
            if year <= 2023:
                hist = self._extract_historical('ENG', 'P1')
                if year not in hist:
                    continue
                year_data_dict = self.master_data['by_year'][str(year)]['ENG']
            else:
                # Use 2030 forecast
                year_data_dict = self.forecasts['ENG']
            
            levels = ['P1', 'P2', 'P3', 'P4', 'P5']
            salaries = []
            
            for level in levels:
                if year <= 2023:
                    if level in self.master_data['by_year'][str(year)]['ENG']:
                        salaries.append(self.master_data['by_year'][str(year)]['ENG'][level])
                else:
                    if level in year_data_dict and isinstance(year_data_dict[level], dict):
                        if '2030' in year_data_dict[level]:
                            salaries.append(year_data_dict[level]['2030'])
            
            if salaries:
                linestyle = '--' if year == 2030 else '-'
                ax.plot(levels, salaries, marker='o', label=str(year), 
                       linewidth=2.5, markersize=7, linestyle=linestyle)
        
        ax.set_xlabel('Career Level', fontweight='bold')
        ax.set_ylabel('Median Base Salary ($CAD)', fontweight='bold')
        ax.set_title('Professional Career Progression (Entry to Expert)')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    def _plot_growth_rates(self, ax):
        """Plot annual salary growth rates by level."""
        
        growth_rates = {}
        
        for level in ['P1', 'P2', 'P3', 'P4', 'P5', 'M1', 'M2', 'M3', 'M4']:
            historical = self._extract_historical('ENG', level)
            
            if len(historical) < 2:
                continue
            
            years_sorted = sorted(historical.keys())
            first_year = historical[years_sorted[0]]
            last_year = historical[years_sorted[-1]]
            
            # CAGR calculation
            years_diff = years_sorted[-1] - years_sorted[0]
            if years_diff > 0:
                cagr = ((last_year / first_year) ** (1 / years_diff) - 1) * 100
                growth_rates[level] = cagr
        
        levels = sorted(growth_rates.keys())
        rates = [growth_rates[l] for l in levels]
        
        colors = ['#2E86AB' if l.startswith('P') else '#A23B72' for l in levels]
        bars = ax.bar(levels, rates, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Add value labels on bars
        for bar, rate in zip(bars, rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        ax.set_xlabel('Career Level', fontweight='bold')
        ax.set_ylabel('Compound Annual Growth Rate (%)', fontweight='bold')
        ax.set_title('Historical Salary Growth Rates (2020-2023)')
        ax.grid(True, alpha=0.3, axis='y')
        ax.axhline(y=0, color='black', linewidth=0.8)

    def _plot_levels_for_profession(self, ax, profession: str, levels: list, title: str):
        """Plot a list of levels for a profession on a single axis (historical + forecast)."""

        colors = plt.cm.viridis(np.linspace(0, 1, len(levels)))

        for level, color in zip(levels, colors):
            # Historical
            historical = self._extract_historical(profession, level)
            if historical:
                years = sorted(historical.keys())
                salaries = [historical[y] for y in years]
                ax.plot(years, salaries, marker='o', linestyle='-', color=color, linewidth=2, label=level)

            # Forecast
            if level in self.forecasts.get(profession, {}):
                forecast = self.forecasts[profession][level]
                f_years = [int(y) for y in sorted(forecast.keys())]
                f_salaries = [forecast[str(y)] for y in f_years]
                ax.plot(f_years, f_salaries, marker='o', linestyle='--', color=color, linewidth=1.5, alpha=0.8)

        ax.set_title(title)
        ax.set_xlabel('Year')
        ax.set_ylabel('Median Base Salary ($CAD)')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
        ax.grid(True, alpha=0.25)
        ax.legend(loc='best', fontsize=8)

    def generate_profession_level_panels(self):
        """Create a 2x2 figure with ENG P1-P5, ENG M1-M5, GEO P1-P5, GEO M1-M5."""

        print("\nGenerating 4-panel level plots (ENG & GEO)...")

        levels_p = ['P1', 'P2', 'P3', 'P4', 'P5']
        levels_m = ['M1', 'M2', 'M3', 'M4', 'M5']

        fig, axs = plt.subplots(2, 2, figsize=(16, 12))

        # ENG P1-P5
        self._plot_levels_for_profession(axs[0, 0], 'ENG', levels_p, 'ENG: P1-P5 (Professional Levels)')

        # ENG M1-M5
        self._plot_levels_for_profession(axs[0, 1], 'ENG', levels_m, 'ENG: M1-M5 (Management Levels)')

        # GEO P1-P5
        self._plot_levels_for_profession(axs[1, 0], 'GEO', levels_p, 'GEO: P1-P5 (Professional Levels)')

        # GEO M1-M5
        self._plot_levels_for_profession(axs[1, 1], 'GEO', levels_m, 'GEO: M1-M5 (Management Levels)')

        plt.tight_layout()
        panel_path = OUTPUT_DIR / 'salary_levels_4panel.png'
        plt.savefig(panel_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {panel_path}")

    def generate_overlay_plot(self):
        """Create a single overlay plot with every career level (ENG & GEO) across years.

        - X axis: Year (historical + forecast)
        - Y axis: Median base salary ($ CAD)
        - ENG lines: solid; GEO lines: dashed
        - Labels: each line annotated at the right edge with level name
        - Output: saves to `outputs/salary_overlay_levels.png`
        """

        print("\nOverlaying all career levels into single plot...")

        # Prepare levels
        eng_levels = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'M1', 'M2', 'M3', 'M4', 'M5']
        geo_levels = eng_levels  # same labels

        fig, ax = plt.subplots(figsize=(14, 8))
        colors = plt.cm.get_cmap('tab20', len(eng_levels))

        # Plot ENG
        for i, level in enumerate(eng_levels):
            # historical
            hist = self._extract_historical('ENG', level)
            if hist:
                years = sorted(hist.keys())
                salaries = [hist[y] for y in years]
                ax.plot(years, salaries, label=f'ENG {level}', color=colors(i), linewidth=2.0)

            # forecast
            if level in self.forecasts.get('ENG', {}):
                forecast = self.forecasts['ENG'][level]
                f_years = [int(y) for y in sorted(forecast.keys())]
                f_salaries = [forecast[str(y)] for y in f_years]
                ax.plot(f_years, f_salaries, linestyle='--', color=colors(i), linewidth=1.5, alpha=0.8)

        # Plot GEO
        # (use dashed lines and slightly lighter colors)
        for i, level in enumerate(geo_levels):
            hist = self._extract_historical('GEO', level)
            if hist:
                years = sorted(hist.keys())
                salaries = [hist[y] for y in years]
                ax.plot(years, salaries, label=f'GEO {level}', color=colors(i), linestyle=':', linewidth=1.5, alpha=0.85)

            if level in self.forecasts.get('GEO', {}):
                forecast = self.forecasts['GEO'][level]
                f_years = [int(y) for y in sorted(forecast.keys())]
                f_salaries = [forecast[str(y)] for y in f_years]
                ax.plot(f_years, f_salaries, linestyle=':', color=colors(i), linewidth=1.25, alpha=0.65)

        # Format
        ax.set_title('APEGA Salary Levels - Historical & Forecast (ENG & GEO)', fontsize=16, fontweight='bold')
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Median Base Salary (CAD)', fontweight='bold')
        ax.grid(True, alpha=0.25)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))

        # Place legend to right with small font
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=8)

        # Annotate end-points for clearer labels (ENG only to reduce clutter)
        for level in eng_levels:
            if level in self.forecasts.get('ENG', {}):
                y = self.forecasts['ENG'][level]['2030']
                ax.annotate(level, xy=(2030, y), xytext=(2031, y), va='center', fontsize=8, color='black')

        # Save to outputs
        overlay_path = OUTPUT_DIR / 'salary_overlay_levels.png'
        plt.tight_layout()
        plt.savefig(overlay_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {overlay_path}")
        
    def generate_profession_overlay(self, profession: str = 'ENG'):
        """Create overlay plot for a specific profession only (ENG or GEO).

        - Profession is 'ENG' or 'GEO'
        - X axis: Year (historical + forecast)
        - Y axis: Median base salary ($ CAD)
        - Lines: solid for historical, dashed for forecast
        - Output: saves to `outputs/salary_overlay_{profession.lower()}_levels.png`
        """

        print(f"\nOverlaying levels for {profession} only...")

        levels = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'M1', 'M2', 'M3', 'M4', 'M5']
        fig, ax = plt.subplots(figsize=(14, 8))
        colors = plt.cm.get_cmap('tab10', len(levels))

        for i, level in enumerate(levels):
            hist = self._extract_historical(profession, level)
            if hist:
                years = sorted(hist.keys())
                salaries = [hist[y] for y in years]
                ax.plot(years, salaries, label=f'{level}', color=colors(i), linewidth=2.0)

            if level in self.forecasts.get(profession, {}):
                forecast = self.forecasts[profession][level]
                f_years = [int(y) for y in sorted(forecast.keys())]
                f_salaries = [forecast[str(y)] for y in f_years]
                ax.plot(f_years, f_salaries, linestyle='--', color=colors(i), linewidth=1.5, alpha=0.85)

        # Format
        ax.set_title(f'APEGA {profession} Salary Levels - Historical & Forecast', fontsize=16, fontweight='bold')
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Median Base Salary (CAD)', fontweight='bold')
        ax.grid(True, alpha=0.25)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))

        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=9)

        # Annotate last forecast point
        for level in levels:
            if level in self.forecasts.get(profession, {}):
                y = self.forecasts[profession][level]['2030']
                ax.annotate(level, xy=(2030, y), xytext=(2031, y), va='center', fontsize=8)

        overlay_path = OUTPUT_DIR / f'salary_overlay_{profession.lower()}_levels.png'
        plt.tight_layout()
        plt.savefig(overlay_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {overlay_path}")

    def generate_engineer_P1_P5_by_year(self):
        """P1-P5 engineers: x axis year, y axis median base salary (save PNG)."""
        levels = ['P1', 'P2', 'P3', 'P4', 'P5']
        fig, ax = plt.subplots(figsize=(12, 8))

        colors = plt.cm.get_cmap('tab10', len(levels))
        for i, level in enumerate(levels):
            hist = self._extract_historical('ENG', level)
            if not hist:
                continue
            years = sorted(hist.keys())
            salaries = [hist[y] for y in years]
            ax.plot(years, salaries, marker='o', linestyle='-', color=colors(i), linewidth=2.2, label=level)

            # Add forecast if available
            if level in self.forecasts.get('ENG', {}):
                forecast = self.forecasts['ENG'][level]
                f_years = [int(y) for y in sorted(forecast.keys())]
                f_salaries = [forecast[str(y)] for y in f_years]
                ax.plot(f_years, f_salaries, marker='o', linestyle='--', color=colors(i), linewidth=1.6, alpha=0.85)

        ax.set_title('ENG: P1 - P5 Median Base Salary by Year', fontsize=14, fontweight='bold')
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Median Base Salary ($CAD)', fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
        ax.grid(True, alpha=0.3)
        ax.legend(title='Level', fontsize=9)

        out = OUTPUT_DIR / 'eng_P1_P5_by_year.png'
        plt.tight_layout()
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {out}")

    def generate_engineer_M1_M5_by_year(self):
        """M1-M5 engineers: x axis year, y axis median base salary (save PNG)."""
        levels = ['M1', 'M2', 'M3', 'M4', 'M5']
        fig, ax = plt.subplots(figsize=(12, 8))

        colors = plt.cm.get_cmap('tab10', len(levels))
        for i, level in enumerate(levels):
            hist = self._extract_historical('ENG', level)
            if not hist:
                continue
            years = sorted(hist.keys())
            salaries = [hist[y] for y in years]
            ax.plot(years, salaries, marker='o', linestyle='-', color=colors(i), linewidth=2.2, label=level)

            # Forecast
            if level in self.forecasts.get('ENG', {}):
                forecast = self.forecasts['ENG'][level]
                f_years = [int(y) for y in sorted(forecast.keys())]
                f_salaries = [forecast[str(y)] for y in f_years]
                ax.plot(f_years, f_salaries, marker='o', linestyle='--', color=colors(i), linewidth=1.6, alpha=0.85)

        ax.set_title('ENG: M1 - M5 Median Base Salary by Year', fontsize=14, fontweight='bold')
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Median Base Salary ($CAD)', fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
        ax.grid(True, alpha=0.3)
        ax.legend(title='Level', fontsize=9)

        out = OUTPUT_DIR / 'eng_M1_M5_by_year.png'
        plt.tight_layout()
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {out}")

    def generate_P1_P5_overlay_by_level(self):
        """P1-P5 engineers plotted by career level (x axis = level), overlayed across years."""
        levels = ['P1', 'P2', 'P3', 'P4', 'P5']
        years = sorted([int(y) for y in self.master_data['by_year'].keys() if int(y) <= 2023])

        fig, ax = plt.subplots(figsize=(10, 7))
        cmap = plt.cm.get_cmap('tab10', len(years)+2)

        for i, year in enumerate(years + [2030]):
            salaries = []
            for level in levels:
                if year <= 2023:
                    val = self.master_data['by_year'].get(str(year), {}).get('ENG', {}).get(level, None)
                else:
                    # use 2030 forecast
                    val = None
                    if level in self.forecasts.get('ENG', {}):
                        val = self.forecasts['ENG'][level].get('2030')

                salaries.append(val if val is not None else np.nan)

            label = str(year)
            linestyle = '--' if year == 2030 else '-'
            ax.plot(levels, salaries, marker='o', linestyle=linestyle, color=cmap(i), label=label, linewidth=2)

        ax.set_title('ENG: P1-P5 Salary by Career Level (Overlay by Year)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Career Level', fontweight='bold')
        ax.set_ylabel('Median Base Salary ($CAD)', fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
        ax.grid(True, alpha=0.25)
        ax.legend(title='Year', fontsize=9)

        out = OUTPUT_DIR / 'eng_P1_P5_by_level_overlay.png'
        plt.tight_layout()
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {out}")

    def generate_historical_growth_rates_by_category(self):
        """Historical CAGR (2020-2023) for engineers (P1-P5) and managers (M1-M5)."""
        # Compute CAGR from 2020 to 2023 where both values exist
        start_year = 2020
        end_year = 2023

        eng_levels = ['P1', 'P2', 'P3', 'P4', 'P5']
        mgr_levels = ['M1', 'M2', 'M3', 'M4', 'M5']

        def compute_cagr(prof, level):
            by_year = self.master_data['by_year']
            try:
                start = by_year[str(start_year)][prof][level]
                end = by_year[str(end_year)][prof][level]
                years = end_year - start_year
                if start > 0 and years > 0:
                    return ((end / start) ** (1 / years) - 1) * 100
            except Exception:
                return np.nan
            return np.nan

        eng_rates = [compute_cagr('ENG', lvl) for lvl in eng_levels]
        mgr_rates = [compute_cagr('ENG', lvl) for lvl in mgr_levels]

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Engineers
        ax = axes[0]
        bars = ax.bar(eng_levels, eng_rates, color='#2E86AB', edgecolor='black')
        ax.set_title('Engineers: CAGR (2020-2023) by Level')
        ax.set_xlabel('Career Level')
        ax.set_ylabel('CAGR (%)')
        ax.grid(True, axis='y', alpha=0.25)
        for bar, val in zip(bars, eng_rates):
            if not np.isnan(val):
                ax.text(bar.get_x()+bar.get_width()/2, val, f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

        # Managers
        ax = axes[1]
        bars = ax.bar(mgr_levels, mgr_rates, color='#A23B72', edgecolor='black')
        ax.set_title('Managers: CAGR (2020-2023) by Level')
        ax.set_xlabel('Career Level')
        ax.set_ylabel('CAGR (%)')
        ax.grid(True, axis='y', alpha=0.25)
        for bar, val in zip(bars, mgr_rates):
            if not np.isnan(val):
                ax.text(bar.get_x()+bar.get_width()/2, val, f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        out = OUTPUT_DIR / 'historical_CAGR_2020_2023_eng_mgr.png'
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {out}")

    def generate_median_and_total_cash_by_level(self, assume_bonus_pct: float = 0.10):
        """Median base salary and (estimated) total cash compensation by level.

        - Uses latest available year for base salary (prefers 2024 if present)
        - If total cash is not present in data, estimates total cash = base * (1 + assume_bonus_pct)
        - Saves output to `outputs/median_base_and_total_cash_by_level.png`
        """
        # Determine latest year available
        years = sorted([int(y) for y in self.master_data['by_year'].keys()])
        latest = years[-1]

        levels = ['P1', 'P2', 'P3', 'P4', 'P5', 'M1', 'M2', 'M3', 'M4', 'M5']
        base_vals = []
        total_cash_vals = []

        for lvl in levels:
            val = self.master_data['by_year'].get(str(latest), {}).get('ENG', {}).get(lvl, np.nan)
            base_vals.append(val if val is not None else np.nan)

            # Attempt to find total cash in data (not present in master) - fallback to estimate
            # (No explicit total cash field in current master data.)
            total_cash_vals.append(val * (1 + assume_bonus_pct) if val is not None else np.nan)

        x = np.arange(len(levels))
        width = 0.35

        fig, ax = plt.subplots(figsize=(14, 7))
        bars1 = ax.bar(x - width/2, base_vals, width, label='Median Base Salary', color='#2E86AB', edgecolor='black')
        bars2 = ax.bar(x + width/2, total_cash_vals, width, label=f'Estimated Total Cash (+{int(assume_bonus_pct*100)}%)', color='#A23B72', edgecolor='black')

        ax.set_xticks(x)
        ax.set_xticklabels(levels)
        ax.set_xlabel('Career Level', fontweight='bold')
        ax.set_ylabel('Salary ($CAD)', fontweight='bold')
        ax.set_title(f'Median Base Salary and Estimated Total Cash by Level ({latest})', fontsize=14, fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
        ax.legend()
        ax.grid(True, axis='y', alpha=0.25)

        # Annotate bars
        for bar in bars1 + bars2:
            height = bar.get_height()
            if not np.isnan(height):
                ax.text(bar.get_x() + bar.get_width()/2, height, f'${int(height):,}', ha='center', va='bottom', fontsize=8)

        out = OUTPUT_DIR / 'median_base_and_total_cash_by_level.png'
        plt.tight_layout()
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"* Saved: {out} (total cash estimated since raw data not available)")


if __name__ == '__main__':
    forecaster = SalaryForecaster()
    forecaster.forecast_all()
    print(f"\n* Forecasting complete! Check '{OUTPUT_DIR}' for outputs.")
