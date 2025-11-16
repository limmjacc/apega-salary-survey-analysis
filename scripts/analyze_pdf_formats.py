#!/usr/bin/env python3
"""
Analyze 2021 and 2024 PDF formats to understand data extraction challenges.
"""

import pdfplumber
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOCS = ROOT / 'docs'

def analyze_pdf(pdf_path, year, sample_pages=5):
    """Analyze PDF structure and content."""
    print(f"\n{'='*70}")
    print(f"ANALYZING {year} PDF: {pdf_path.name}")
    print(f"{'='*70}\n")
    
    try:
        pdf = pdfplumber.open(str(pdf_path))
        print(f"Total pages: {len(pdf.pages)}\n")
        
        # Sample pages
        for page_idx in range(min(sample_pages, len(pdf.pages))):
            page = pdf.pages[page_idx]
            text = page.extract_text()
            tables = page.extract_tables()
            
            print(f"Page {page_idx + 1}:")
            print(f"  - Tables found: {len(tables) if tables else 0}")
            
            if text:
                # Look for salary patterns
                salaries = re.findall(r'\$[\d,]+', text)
                print(f"  - Salary values: {len(salaries)}")
                
                # Look for career levels
                levels = re.findall(r'\b(P[1-6]|M[1-5])\b', text)
                print(f"  - Career levels mentioned: {len(set(levels))} unique")
                
                # Look for org count
                org_match = re.search(r'(\d+)\s+(?:organizations|Participating\s+Organizations)', text, re.IGNORECASE)
                if org_match:
                    print(f"  - Organization count: {org_match.group(1)}")
                
                # Show preview
                print(f"  - Text preview (first 150 chars):\n    {text[:150]}\n")
            else:
                print(f"  - NO TEXT EXTRACTED\n")
        
        pdf.close()
        
    except Exception as e:
        print(f"ERROR: {e}\n")

if __name__ == '__main__':
    analyze_pdf(DOCS / '2021' / 'apega_salary_survey_2021.pdf', '2021', 8)
    analyze_pdf(DOCS / '2024' / 'apega_salary_survey_2024.pdf', '2024', 8)
