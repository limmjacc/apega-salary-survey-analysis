#!/usr/bin/env python3
"""
Extract salary data from 2021 PDF using OCR (Tesseract).
(Archived - kept for reference.)
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

# (Original function bodies preserved for historical/backup purposes.)
