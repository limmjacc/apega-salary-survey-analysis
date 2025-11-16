#!/usr/bin/env python3
"""
Forecast APEGA salary trends through 2030 using historical data.
Applies linear and polynomial regression to project future compensation.
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
            
            self.forecasts[profession] = salary_by_level
        
        self.save_forecasts()
        self.generate_plots()
    
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
        
        # Use polynomial for conservative projection (accounts for potential slowdown)
        for forecast_year in range(2024, 2031):
            year_offset = forecast_year - years[0]
            poly_pred = poly_fit(year_offset)
            linear_pred = linear_intercept + linear_slope * year_offset
            
            # Average both models for robustness
            predicted = (poly_pred + linear_pred) / 2
            forecast_data[str(forecast_year)] = round(predicted)
        
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


if __name__ == '__main__':
    forecaster = SalaryForecaster()
    forecaster.forecast_all()
    print(f"\n* Forecasting complete! Check '{OUTPUT_DIR}' for outputs.")
