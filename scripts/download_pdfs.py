"""
Download and manage APEGA salary survey PDFs.

Status: Active
Usage: python scripts/download_pdfs.py
Output: Downloads PDFs to `docs/YYYY/apega_salary_survey_YYYY.pdf`

CURRENT STATUS (as of Nov 2025):
- 2020-2024: Available as apega_salary_survey_YYYY.pdf in docs/YYYY/
- 2013-2019: Corrupted Wayback snapshots (HTML instead of PDF); documented in docs/2013-2019/README.txt

USAGE:
1. To re-download available years (2020-2024):
   python scripts/download_pdfs.py

2. To scrape a Scribd document (e.g., for future years not on APEGA site):
   python scripts/scrape_scribd_2024.py <scribd_url>

3. Naming convention: apega_salary_survey_YYYY.pdf (all years use this standard)

"""
import hashlib
import os
import requests
from urllib.parse import quote_plus
import re

# Destination folder
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
os.makedirs(DOCS_DIR, exist_ok=True)

# Available downloads (years where PDFs are accessible)
PDF_LINKS = {
    'apega-salary-survey-member-report-2023.pdf': [
        'https://www.apega.ca/docs/default-source/pdfs/apega-salary-survey-member-report-2023.pdf',
        'https://web.archive.org/web/20240311204416/https://www.apega.ca/docs/default-source/pdfs/apega-salary-survey-member-report-2023.pdf'
    ],
    'apega-member-report-2022.pdf': [
        'https://www.apega.ca/docs/default-source/pdfs/apega-member-report-2022.pdf',
        'https://web.archive.org/web/20231201101111/https://www.apega.ca/docs/default-source/pdfs/apega-member-report-2022.pdf'
    ],
    '2021-member-report.pdf': [
        'https://www.apega.ca/docs/default-source/pdfs/2021-member-report.pdf',
        'https://web.archive.org/web/20211222174222/https://www.apega.ca/docs/default-source/pdfs/2021-member-report.pdf'
    ],
    'apega-2020-salary-survey-member-report.pdf': [
        'https://www.apega.ca/docs/default-source/pdfs/apega-2020-salary-survey-member-report.pdf',
        'https://web.archive.org/web/20211222174222/https://www.apega.ca/docs/default-source/pdfs/apega-2020-salary-survey-member-report.pdf'
    ],
}

# Note: 2013-2019 PDFs are not available (corrupted Wayback snapshots contain HTML, not PDF binary)
# See docs/2013-2019/README.txt for recovery attempts and details.


def download_file(url, local_path):
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(4096), b""):
            h.update(b)
    return h.hexdigest()


def main():
    """Download available PDFs and organize into year folders with standard naming."""
    results = []

    for filename, url_candidates in PDF_LINKS.items():
        # Extract year from filename or URLs
        m = re.search(r"(19|20)\d{2}", filename)
        if m:
            year = m.group(0)
        else:
            year = None
            for u in url_candidates:
                mm = re.search(r"(19|20)\d{2}", u)
                if mm:
                    year = mm.group(0)
                    break
        if not year:
            year = 'unknown'

        # Classify as salary_survey or member_report
        t = 'salary_survey'
        if 'member' in filename.lower():
            t = 'member_report'

        # Standard naming: apega_salary_survey_YYYY.pdf (using salary_survey for all)
        new_filename = f"apega_salary_survey_{year}.pdf"
        local_dir = os.path.join(DOCS_DIR, year)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, new_filename)
        
        if os.path.exists(local_path):
            print(f"Already exists: {filename} → {new_filename}")
            results.append((filename, local_path, 'already-exists'))
            continue

        success = False
        for url in url_candidates:
            print(f"Attempting: {url}")
            if download_file(url, local_path):
                checksum = sha256_of_file(local_path)
                print(f"✓ Downloaded: {new_filename} (sha256={checksum[:16]}...)")
                results.append((filename, url, checksum))
                success = True
                break

        if not success:
            print(f"✗ Failed to download {filename}")
            results.append((filename, None, 'failed'))

    print(f"\nDone. PDFs saved to docs/YYYY/ with standard naming: apega_salary_survey_YYYY.pdf")
    print("For 2013-2019 (unavailable), see docs/2013-2019/README.txt")


if __name__ == '__main__':
    main()
