#!/usr/bin/env python3
"""
Extract and parse salary data from APEGA PDFs comprehensively.
Handles tables, text blocks, and structured data extraction.

Status: Active
Usage: python scripts/extract_salary_data.py
Output: `data/<year>_raw_tables.json`, and parsed salary tables in memory
Note: This is the main parser used during automated table extraction.
"""

import os
from pathlib import Path
import json
from PyPDF2 import PdfReader
import pdfplumber
import re
from typing import Dict, List, Tuple, Any
import pandas as pd

ROOT = Path(__file__).parent.parent
DOCS = ROOT / 'docs'
OUTPUT_DIR = ROOT / 'data'
OUTPUT_DIR.mkdir(exist_ok=True)


class APEGASalaryParser:
    """Parse APEGA salary survey PDFs and extract structured data."""
    
    def __init__(self):
        self.data_by_year = {}
        self.all_tables = {}
    
    def extract_from_all_pdfs(self):
        """Find and parse all salary survey PDFs."""
        pdf_files = sorted(DOCS.glob('*/apega_salary_survey_*.pdf'))
        print(f"Found {len(pdf_files)} PDFs to parse:")
        for pdf in pdf_files:
            print(f"  {pdf.parent.name}: {pdf.name}")
        
        for pdf_path in pdf_files:
            year = pdf_path.parent.name
            print(f"\n{'='*70}")
            print(f"Parsing {year}...")
            print(f"{'='*70}")
            try:
                self.extract_from_pdf(str(pdf_path), year)
            except Exception as e:
                print(f"ERROR parsing {year}: {e}")
    
    def extract_from_pdf(self, pdf_path: str, year: str):
        """Extract all data from a single PDF."""
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            print(f"Total pages: {num_pages}")
            
            # Try to extract tables from all pages
            all_tables = []
            text_blocks = {}
            
            for page_num, page in enumerate(pdf.pages):
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    print(f"  Page {page_num + 1}: Found {len(tables)} table(s)")
                    all_tables.extend([(page_num, t) for t in tables])
                
                # Extract raw text for keyword searching
                text = page.extract_text()
                if text:
                    text_blocks[page_num] = text
            
            print(f"Total tables found: {len(all_tables)}")
            
            # Store raw tables for inspection
            self.all_tables[year] = all_tables
            
            # Parse and organize data
            parsed_data = self._parse_salary_data(all_tables, text_blocks, year)
            self.data_by_year[year] = parsed_data
            
            # Save raw tables for debugging
            self._save_raw_tables(year, all_tables)
    
    def _parse_salary_data(self, tables: List, text_blocks: Dict, year: str) -> Dict[str, Any]:
        """Parse and organize extracted tables into salary categories."""
        data = {
            'year': int(year),
            'organization_stats': {},
            'headcount': {},
            'compensation': {
                'ENG': {},
                'GEO': {}
            },
            'demographics': {
                'gender': {}
            },
            'work_arrangements': {},
            'career_levels': {
                'ENG': {'P': {}, 'M': {}},
                'GEO': {'P': {}, 'M': {}}
            },
            'raw_text': ' '.join(text_blocks.values())
        }
        
        # Try to extract key statistics from text
        self._extract_org_stats(data, text_blocks)
        self._extract_compensation_data(data, tables)
        self._extract_demographic_data(data, tables)
        self._extract_work_arrangements(data, text_blocks)
        
        return data
    
    def _extract_org_stats(self, data: Dict, text_blocks: Dict):
        """Extract organization statistics."""
        full_text = ' '.join(text_blocks.values())
        
        # Look for number of organizations
        org_patterns = [
            r'(\d+)\s+(?:participating\s+)?organizations?',
            r'(?:number|count)\s+of\s+organizations?:\s*(\d+)',
        ]
        for pattern in org_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data['organization_stats']['num_organizations'] = int(match.group(1))
                print(f"  Found {match.group(1)} organizations")
                break
        
        # Look for respondent counts
        respondent_patterns = [
            r'(\d+)\s+(?:respondents?|incumbents?)',
            r'(?:respondents?|incumbents?):\s*(\d+)',
        ]
        for pattern in respondent_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data['organization_stats']['num_respondents'] = int(match.group(1))
                print(f"  Found {match.group(1)} respondents")
                break
    
    def _extract_compensation_data(self, data: Dict, tables: List):
        """Extract median salary and compensation by level."""
        for page_num, table in tables:
            table_df = pd.DataFrame(table[1:], columns=table[0] if table else [])
            
            # Look for compensation-related columns
            for col in table_df.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['salary', 'compensation', 'cash', 'base']):
                    print(f"  Page {page_num}: Found compensation column: {col}")
                    # Try to identify if it's ENG or GEO
                    profession = 'ENG' if 'engineer' in ' '.join(str(c).lower() for c in table_df.columns) else 'GEO' if 'geoscientist' in ' '.join(str(c).lower() for c in table_df.columns) else 'UNKNOWN'
                    if profession != 'UNKNOWN':
                        if 'median' in col_lower:
                            data['compensation'][profession]['median'] = table_df[[col]]
    
    def _extract_demographic_data(self, data: Dict, tables: List):
        """Extract gender and demographic breakdowns."""
        for page_num, table in tables:
            if not table:
                continue
            table_df = pd.DataFrame(table[1:], columns=table[0])
            
            # Look for gender-related rows/columns
            for col in table_df.columns:
                if 'gender' in str(col).lower() or 'male' in str(col).lower() or 'female' in str(col).lower():
                    print(f"  Page {page_num}: Found gender data in column: {col}")
                    data['demographics']['gender'] = table_df
    
    def _extract_work_arrangements(self, data: Dict, text_blocks: Dict):
        """Extract remote/hybrid work percentages."""
        full_text = ' '.join(text_blocks.values())
        
        patterns = {
            'remote': r'(\d+)%?\s*(?:fully\s+)?remote',
            'hybrid': r'(\d+)%?\s*hybrid',
            'on_site': r'(\d+)%?\s*(?:on[\s-]?site|office)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data['work_arrangements'][key] = int(match.group(1))
                print(f"  Found {match.group(1)}% {key}")
    
    def _save_raw_tables(self, year: str, tables: List):
        """Save raw table data for inspection."""
        output_file = OUTPUT_DIR / f'{year}_raw_tables.json'
        
        serializable_tables = []
        for page_num, table in tables:
            # Convert table to list of lists (serialize-friendly)
            serialized_table = []
            for row in table:
                serialized_row = []
                for cell in row:
                    # Convert to string, handling None
                    if cell is None:
                        serialized_row.append('')
                    else:
                        serialized_row.append(str(cell))
                serialized_table.append(serialized_row)
            serializable_tables.append({
                'page': page_num + 1,
                'table': serialized_table
            })
        
        with open(output_file, 'w') as f:
            json.dump(serializable_tables, f, indent=2)
        print(f"  Saved raw tables to: {output_file}")
    
    def save_parsed_data(self):
        """Save parsed data to JSON."""
        output_file = OUTPUT_DIR / 'salary_data_parsed.json'
        
        # Make DataFrames JSON-serializable
        serializable_data = {}
        for year, data in self.data_by_year.items():
            serializable_year = {}
            for key, value in data.items():
                if isinstance(value, pd.DataFrame):
                    serializable_year[key] = value.to_dict(orient='records')
                elif isinstance(value, dict):
                    serializable_year[key] = {}
                    for k, v in value.items():
                        if isinstance(v, pd.DataFrame):
                            serializable_year[key][k] = v.to_dict(orient='records')
                        else:
                            serializable_year[key][k] = v
                else:
                    serializable_year[key] = value
            serializable_data[year] = serializable_year
        
        with open(output_file, 'w') as f:
            json.dump(serializable_data, f, indent=2)
        print(f"\nSaved parsed data to: {output_file}")
    
    def print_summary(self):
        """Print summary of parsed data."""
        print(f"\n{'='*70}")
        print("SUMMARY OF PARSED DATA")
        print(f"{'='*70}")
        for year, data in sorted(self.data_by_year.items()):
            print(f"\n{year}:")
            print(f"  Organization stats: {data.get('organization_stats', {})}")
            print(f"  Work arrangements: {data.get('work_arrangements', {})}")


def main():
    parser = APEGASalaryParser()
    parser.extract_from_all_pdfs()
    parser.save_parsed_data()
    parser.print_summary()


if __name__ == '__main__':
    main()
