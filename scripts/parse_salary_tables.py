#!/usr/bin/env python3
"""
Advanced APEGA salary table parser - extracts structured compensation data.
Handles year-specific format variations and builds normalized salary dataset.

Status: Active
Usage: python scripts/parse_salary_tables.py
Output: `data/salary_master.json` (consolidated dataset)
"""

import os
from pathlib import Path
import json
import re
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import pdfplumber
from PyPDF2 import PdfReader

ROOT = Path(__file__).parent.parent
DOCS = ROOT / 'docs'
OUTPUT_DIR = ROOT / 'data'
OUTPUT_DIR.mkdir(exist_ok=True)


class SalaryTableParser:
    """Parse and extract structured salary data from APEGA PDFs."""
    
    CAREER_LEVELS = {
        'P': ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'],
        'M': ['M1', 'M2', 'M3', 'M4', 'M5']
    }
    
    def __init__(self):
        self.salary_data = {}
        self.gender_data = {}
        self.org_stats = {}
        self.work_arrangements = {}
    
    def parse_all_years(self):
        """Parse all available salary survey PDFs."""
        pdf_files = sorted(DOCS.glob('*/apega_salary_survey_*.pdf'))
        print(f"Parsing {len(pdf_files)} PDFs for salary data:\n")
        
        for pdf_path in pdf_files:
            year = int(pdf_path.parent.name)
            print(f"[{year}] {pdf_path.name}")
            try:
                self.parse_year(str(pdf_path), year)
            except Exception as e:
                print(f"   ⚠ Error: {e}")
        
        self.save_master_dataset()
        self.generate_summary()
    
    def parse_year(self, pdf_path: str, year: int):
        """Extract all salary tables for a given year."""
        with pdfplumber.open(pdf_path) as pdf:
            # Look for career level salary tables
            salary_tables_eng = {}
            salary_tables_geo = {}
            org_count = None
            incumbent_count = None
            gender_split = {}
            remote_work_pct = None
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue
                
                # Extract organization count
                if org_count is None:
                    org_match = re.search(r'(?:Number of organizations|Participating\s+Organizations)\s*:?[\s\n]+(\d+)', text, re.IGNORECASE)
                    if org_match:
                        org_count = int(org_match.group(1))
                
                # Extract incumbent count
                if incumbent_count is None:
                    inc_match = re.search(r'(?:Number of incumbents|incumbents)\s*:?[\s\n]+(\d+(?:,\d+)?)', text, re.IGNORECASE)
                    if inc_match:
                        incumbent_count = int(inc_match.group(1).replace(',', ''))
                
                # Extract gender split (look for patterns like "95% 5% Engineers Geoscientists")
                if not gender_split:
                    # Common pattern: percentage engineers, percentage geoscientists
                    gender_patterns = [
                        r'(\d+)%\s+(?:Engineers|ENG).*?(\d+)%\s+(?:Geoscientists|GEO)',
                        r'(\d+)%\s+(\d+)%\s+Engineers\s+Geoscientists'
                    ]
                    for pattern in gender_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            gender_split = {
                                'engineers_pct': int(match.group(1)),
                                'geoscientists_pct': int(match.group(2))
                            }
                            break
                
                # Extract remote work percentage
                if remote_work_pct is None and year >= 2023:
                    remote_match = re.search(r'(?:remote|hybrid).*?(\d+)%', text, re.IGNORECASE)
                    if remote_match:
                        remote_work_pct = int(remote_match.group(1))
                
                # Extract salary tables using pdfplumber's table detection
                tables = page.extract_tables()
                if tables:
                    self._process_tables(tables, text, year, salary_tables_eng, salary_tables_geo)
            
            # Store parsed data for this year
            if not any([salary_tables_eng, salary_tables_geo]):
                print(f"   ℹ No salary tables extracted")
            else:
                print(f"   ✓ Extracted: {len(salary_tables_eng)} ENG, {len(salary_tables_geo)} GEO levels")
            
            self.salary_data[year] = {
                'ENG': salary_tables_eng,
                'GEO': salary_tables_geo
            }
            
            if org_count:
                self.org_stats[year] = org_count
                print(f"   ✓ Organizations: {org_count}")
            
            if gender_split:
                self.gender_data[year] = gender_split
                print(f"   ✓ Gender split: {gender_split}")
            
            if remote_work_pct:
                self.work_arrangements[year] = {'remote_or_hybrid_pct': remote_work_pct}
                print(f"   ✓ Remote/Hybrid: {remote_work_pct}%")
    
    def _process_tables(self, tables: List, text: str, year: int, 
                       salary_tables_eng: Dict, salary_tables_geo: Dict):
        """Extract salary data from tables."""
        
        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue
            
            # Convert table to DataFrame for easier processing
            df = pd.DataFrame(table)
            df_text = df.to_string()
            
            # Look for salary table indicators
            has_salary_data = any(keyword in df_text for keyword in 
                                 ['Median Base', 'Annual Base Salary', 'Base Salary', 'P1', 'P2', 'M1', 'M2'])
            
            if not has_salary_data:
                continue
            
            # Look for professional levels (P1-P5, M1-M5)
            profession_type = None
            if any(word in df_text for word in ['ENG', 'Engineering']):
                profession_type = 'ENG'
            elif any(word in df_text for word in ['GEO', 'Geoscience']):
                profession_type = 'GEO'
            
            if not profession_type:
                continue
            
            # Extract career level and salary mappings
            for row_idx, row in enumerate(table):
                if not row:
                    continue
                
                row_text = ' '.join(str(cell) for cell in row if cell)
                
                # Look for career level indicators
                for level_type in ['P', 'M']:
                    for level_num in range(1, 7):
                        level = f"{level_type}{level_num}"
                        if level not in row_text:
                            continue
                        
                        # Find salary value in this row or nearby cells
                        for cell in row:
                            if not cell:
                                continue
                            salary_match = re.search(r'\$?([\d,]+)', str(cell))
                            if salary_match:
                                try:
                                    salary = int(salary_match.group(1).replace(',', '').replace('$', ''))
                                    # Only accept reasonable salary values (>20k, <300k)
                                    if 20000 <= salary <= 300000:
                                        target_dict = salary_tables_eng if profession_type == 'ENG' else salary_tables_geo
                                        if level not in target_dict:
                                            target_dict[level] = salary
                                        break
                                except ValueError:
                                    continue
    
    def save_master_dataset(self):
        """Save comprehensive salary dataset to JSON."""
        output_path = OUTPUT_DIR / 'salary_master.json'
        
        master_data = {
            'metadata': {
                'years': sorted(self.salary_data.keys()),
                'professions': ['ENG', 'GEO'],
                'levels': self.CAREER_LEVELS
            },
            'by_year': {}
        }
        
        for year in sorted(self.salary_data.keys()):
            master_data['by_year'][str(year)] = {
                'ENG': self.salary_data[year]['ENG'],
                'GEO': self.salary_data[year]['GEO'],
                'org_count': self.org_stats.get(year),
                'gender': self.gender_data.get(year),
                'work_arrangements': self.work_arrangements.get(year)
            }
        
        with open(output_path, 'w') as f:
            json.dump(master_data, f, indent=2)
        
        print(f"\n✓ Saved master dataset to: {output_path}")
    
    def generate_summary(self):
        """Generate and display summary statistics."""
        print(f"\n{'='*70}")
        print("SALARY DATA EXTRACTION SUMMARY")
        print(f"{'='*70}\n")
        
        for year in sorted(self.salary_data.keys()):
            eng = self.salary_data[year]['ENG']
            geo = self.salary_data[year]['GEO']
            
            print(f"{year}:")
            if eng:
                levels = sorted(eng.keys())
                salaries = [eng[l] for l in levels]
                print(f"  ENG: {len(eng)} levels, range ${min(salaries):,} - ${max(salaries):,}")
                # Show trend
                p1_salary = eng.get('P1', 0)
                p5_salary = eng.get('P5', 0)
                if p1_salary and p5_salary:
                    growth = ((p5_salary - p1_salary) / p1_salary) * 100
                    print(f"       P1: ${p1_salary:,} → P5: ${p5_salary:,} (+{growth:.1f}%)")
            
            if geo:
                levels = sorted(geo.keys())
                salaries = [geo[l] for l in levels]
                print(f"  GEO: {len(geo)} levels, range ${min(salaries):,} - ${max(salaries):,}")
                p1_salary = geo.get('P1', 0)
                p5_salary = geo.get('P5', 0)
                if p1_salary and p5_salary:
                    growth = ((p5_salary - p1_salary) / p1_salary) * 100
                    print(f"       P1: ${p1_salary:,} → P5: ${p5_salary:,} (+{growth:.1f}%)")
            
            org = self.org_stats.get(year)
            if org:
                print(f"  Organizations: {org}")
            
            gender = self.gender_data.get(year)
            if gender:
                print(f"  Gender split: {gender['engineers_pct']}% ENG, {gender['geoscientists_pct']}% GEO")
            
            work = self.work_arrangements.get(year)
            if work:
                print(f"  Remote/Hybrid: {work.get('remote_or_hybrid_pct')}%")
            
            print()


if __name__ == '__main__':
    parser = SalaryTableParser()
    parser.parse_all_years()
