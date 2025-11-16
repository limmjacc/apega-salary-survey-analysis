#!/usr/bin/env python3
"""
Extract salary data from 2024 PDF using OCR and table recognition.
The 2024 PDF is Scribd-sourced (from assembled images) and contains structured data.
"""

import re
import json
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np

ROOT = Path(__file__).parent.parent
DOCS = ROOT / 'docs'
OUTPUT_DIR = ROOT / 'data'
OUTPUT_DIR.mkdir(exist_ok=True)


class OCRExtractor2024:
    """Extract 2024 salary data using OCR with table-aware processing."""
    
    def __init__(self):
        self.year = 2024
        self.data = {
            'year': self.year,
            'organization_stats': {},
            'compensation': {'ENG': {}, 'GEO': {}},
            'demographics': {'gender': {}},
            'work_arrangements': {},
            'career_levels': {'ENG': {'P': {}, 'M': {}}, 'GEO': {'P': {}, 'M': {}}},
            'raw_ocr_text': ''
        }
    
    def extract_from_pdf(self, pdf_path):
        """Convert PDF to images and extract text via OCR."""
        print(f"Converting PDF to images...")
        try:
            # Convert PDF pages to images (200 DPI is faster, enough for OCR)
            images = convert_from_path(str(pdf_path), dpi=200)
            print(f"Converted {len(images)} pages to images\n")
            
            all_text = []
            
            # OCR each page with enhancement
            for page_num, image in enumerate(images, 1):
                print(f"Processing page {page_num}/{len(images)}...", end='', flush=True)
                
                # Enhance image for OCR
                enhanced = self._enhance_image(image)
                
                # OCR with config for better table recognition
                text = pytesseract.image_to_string(
                    enhanced,
                    config='--psm 6'  # PSM 6: Assume single column of text
                )
                all_text.append(text)
                print(" ✓")
            
            self.data['raw_ocr_text'] = '\n---PAGE BREAK---\n'.join(all_text)
            self._parse_salary_data(self.data['raw_ocr_text'])
            return True
            
        except Exception as e:
            print(f"ERROR during OCR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _enhance_image(self, image):
        """Enhance image for better OCR performance."""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2)
        
        return image
    
    def _parse_salary_data(self, text):
        """Parse OCR text for salary data."""
        
        # Extract organization count
        org_patterns = [
            r'(\d+)\s+(?:companies|organizations|Participating\s+Organizations)',
            r'Number of organizations\s*:?\s*(\d+)',
        ]
        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.data['organization_stats']['num_organizations'] = int(match.group(1))
                print(f"  Found {match.group(1)} organizations")
                break
        
        # Extract incumbent count
        inc_patterns = [
            r'(?:Number of )?incumbents\s*:?\s*(\d+(?:,\d+)?)',
            r'(\d+(?:,\d+)?)\s+(?:incumbents|professional)',
        ]
        for pattern in inc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    inc_count = int(match.group(1).replace(',', ''))
                    if inc_count > 100:  # Sanity check
                        print(f"  Found {inc_count:,} incumbents")
                        break
                except ValueError:
                    continue
        
        # Extract gender split
        gender_patterns = [
            r'(\d+)%\s+(?:Engineers|ENG).*?(\d+)%\s+(?:Geoscientists|GEO)',
            r'(\d+)%\s+(\d+)%\s+Engineers\s+Geoscientists',
        ]
        for pattern in gender_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                self.data['demographics']['gender'] = {
                    'engineers_pct': int(match.group(1)),
                    'geoscientists_pct': int(match.group(2))
                }
                print(f"  Found gender split: {match.group(1)}% ENG, {match.group(2)}% GEO")
                break
        
        # Extract remote/hybrid percentage
        remote_patterns = [
            r'(?:remote|hybrid).*?(\d+)%',
            r'(\d+)%.*?(?:remote|hybrid)',
        ]
        for pattern in remote_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pct = int(match.group(1))
                if 10 <= pct <= 100:  # Sanity check
                    self.data['work_arrangements']['remote_or_hybrid_pct'] = pct
                    print(f"  Found {pct}% remote/hybrid")
                    break
        
        # Extract salary by career level
        self._extract_career_levels(text)
    
    def _extract_career_levels(self, text):
        """Extract salary data by career level."""
        
        # Split by page to identify context (ENG vs GEO pages)
        pages = text.split('---PAGE BREAK---')
        
        for page_idx, page_text in enumerate(pages):
            # Identify which profession this page covers
            is_eng = 'Engineering' in page_text or 'ENG' in page_text
            is_geo = 'Geoscience' in page_text or 'GEO' in page_text
            
            if not (is_eng or is_geo):
                continue
            
            profession = 'ENG' if is_eng else 'GEO'
            
            # Extract salaries for each level
            # Pattern: Level (P1, M1, etc.) followed by salary
            level_salary_pattern = r'(?:^|\s)(P[1-6]|M[1-5])\s+(?:\$|[\w\s]{0,30}?\$)([\d,]+)'
            
            for match in re.finditer(level_salary_pattern, page_text, re.IGNORECASE | re.MULTILINE):
                level = match.group(1).upper()
                try:
                    salary_str = match.group(2).replace(',', '')
                    salary = int(salary_str)
                    
                    # Validate salary range
                    if 30000 <= salary <= 400000:
                        if level not in self.data['compensation'][profession]:
                            self.data['compensation'][profession][level] = salary
                        else:
                            # Average if we see multiple instances
                            existing = self.data['compensation'][profession][level]
                            self.data['compensation'][profession][level] = (existing + salary) // 2
                except ValueError:
                    continue
        
        # Print found levels
        for profession in ['ENG', 'GEO']:
            if self.data['compensation'][profession]:
                print(f"  {profession}: {len(self.data['compensation'][profession])} levels found")
    
    def save_results(self):
        """Save extracted data to JSON."""
        output_path = OUTPUT_DIR / 'salary_data_2024.json'
        
        with open(output_path, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        print(f"\n✓ Saved 2024 OCR extraction to: {output_path}")
        
        # Also append to master if it exists
        master_path = OUTPUT_DIR / 'salary_master.json'
        if master_path.exists():
            with open(master_path, 'r') as f:
                master = json.load(f)
            
            master['by_year']['2024'] = {
                'ENG': self.data['compensation']['ENG'],
                'GEO': self.data['compensation']['GEO'],
                'org_count': self.data['organization_stats'].get('num_organizations'),
                'gender': self.data['demographics'].get('gender'),
                'work_arrangements': self.data['work_arrangements'] if self.data['work_arrangements'] else None
            }
            
            with open(master_path, 'w') as f:
                json.dump(master, f, indent=2)
            
            print(f"✓ Updated salary_master.json with 2024 data")


if __name__ == '__main__':
    pdf_path = DOCS / '2024' / 'apega_salary_survey_2024.pdf'
    
    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} not found")
        exit(1)
    
    print(f"Extracting 2024 salary data via OCR...")
    print(f"{'='*70}\n")
    
    extractor = OCRExtractor2024()
    if extractor.extract_from_pdf(pdf_path):
        print(f"\n{'='*70}")
        print("Extracted Data Summary:")
        print(f"{'='*70}")
        print(f"Organization count: {extractor.data['organization_stats'].get('num_organizations', 'N/A')}")
        print(f"Gender split: {extractor.data['demographics']['gender']}")
        print(f"Work arrangements: {extractor.data['work_arrangements']}")
        print(f"ENG levels found: {len(extractor.data['compensation']['ENG'])}")
        print(f"GEO levels found: {len(extractor.data['compensation']['GEO'])}")
        
        extractor.save_results()
    else:
        print("Failed to extract data")
