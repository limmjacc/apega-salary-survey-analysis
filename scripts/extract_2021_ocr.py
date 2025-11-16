#!/usr/bin/env python3
"""
Extract salary data from 2021 PDF using OCR (Tesseract).
The 2021 PDF has font corruption but OCR can recover the text content.
"""

import re
import json
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

ROOT = Path(__file__).parent.parent
DOCS = ROOT / 'docs'
OUTPUT_DIR = ROOT / 'data'
OUTPUT_DIR.mkdir(exist_ok=True)


class OCRExtractor2021:
    """Extract 2021 salary data using OCR."""
    
    def __init__(self):
        self.year = 2021
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
            # Convert PDF pages to images
            images = convert_from_path(str(pdf_path), dpi=300)
            print(f"Converted {len(images)} pages to images")
            
            all_text = []
            
            # OCR each page
            for page_num, image in enumerate(images, 1):
                print(f"  OCR page {page_num}/{len(images)}...", end='', flush=True)
                
                # Enhance image for better OCR
                image = image.convert('L')  # Grayscale
                
                # OCR
                text = pytesseract.image_to_string(image)
                all_text.append(text)
                print(" ✓")
            
            self.data['raw_ocr_text'] = '\n'.join(all_text)
            self._parse_salary_data(self.data['raw_ocr_text'])
            return True
            
        except Exception as e:
            print(f"ERROR during OCR: {e}")
            return False
    
    def _parse_salary_data(self, text):
        """Parse extracted text for salary data."""
        
        # Extract organization count
        org_patterns = [
            r'(\d+)\s+(?:organizations|permit holders|Participating\s+Organizations)',
            r'Number of organizations\s*:?\s*(\d+)',
        ]
        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.data['organization_stats']['num_organizations'] = int(match.group(1))
                print(f"  Found {match.group(1)} organizations")
                break
        
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
        
        # Extract salary by career level using regex patterns
        # Pattern: Level code (P1, M1, etc.) followed by salary values
        self._extract_career_levels(text)
    
    def _extract_career_levels(self, text):
        """Extract salary data by career level."""
        
        # Look for patterns like:
        # P1 $68,890 or P1 Entry Professional $68,890
        # M1 $120,000 or M1 Team Leader $120,000
        
        profession = None
        
        # Identify profession context
        if 'Engineering' in text:
            profession = 'ENG'
        elif 'Geoscience' in text:
            profession = 'GEO'
        
        if not profession:
            print("  Could not identify profession")
            return
        
        # Extract salaries for each level
        for level_type in ['P', 'M']:
            for level_num in range(1, 7):
                level = f"{level_type}{level_num}"
                
                # Pattern: Level mentioned followed by salary within ~200 chars
                pattern = rf'{level}\s+(?:Entry|Experienced|Senior|Specialist|Expert|Team Leader|Manager)?.*?(\$[\d,]+)'
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    try:
                        salary_str = match.group(1).replace('$', '').replace(',', '')
                        salary = int(salary_str)
                        
                        # Validate salary range
                        if 20000 <= salary <= 500000:
                            if level not in self.data['compensation'][profession]:
                                self.data['compensation'][profession][level] = salary
                                print(f"  {level}: ${salary:,}")
                            break
                    except ValueError:
                        continue
    
    def save_results(self):
        """Save extracted data to JSON."""
        output_path = OUTPUT_DIR / 'salary_data_2021.json'
        
        with open(output_path, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        print(f"\n✓ Saved 2021 OCR extraction to: {output_path}")
        
        # Also append to master if it exists
        master_path = OUTPUT_DIR / 'salary_master.json'
        if master_path.exists():
            with open(master_path, 'r') as f:
                master = json.load(f)
            
            master['by_year']['2021'] = {
                'ENG': self.data['compensation']['ENG'],
                'GEO': self.data['compensation']['GEO'],
                'org_count': self.data['organization_stats'].get('num_organizations'),
                'gender': self.data['demographics'].get('gender'),
                'work_arrangements': self.data['work_arrangements'] if self.data['work_arrangements'] else None
            }
            
            with open(master_path, 'w') as f:
                json.dump(master, f, indent=2)
            
            print(f"✓ Updated salary_master.json with 2021 data")


if __name__ == '__main__':
    pdf_path = DOCS / '2021' / 'apega_salary_survey_2021.pdf'
    
    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} not found")
        exit(1)
    
    print(f"Extracting 2021 salary data via OCR...")
    print(f"{'='*70}\n")
    
    extractor = OCRExtractor2021()
    if extractor.extract_from_pdf(pdf_path):
        print(f"\n{'='*70}")
        print("Extracted Data Summary:")
        print(f"{'='*70}")
        print(f"Organization count: {extractor.data['organization_stats'].get('num_organizations', 'N/A')}")
        print(f"Gender split: {extractor.data['demographics']['gender']}")
        print(f"ENG levels found: {len(extractor.data['compensation']['ENG'])}")
        print(f"GEO levels found: {len(extractor.data['compensation']['GEO'])}")
        
        extractor.save_results()
    else:
        print("Failed to extract data")
