# apega-salary-survey-analysis

A project to collect and archive APEGA Salary Survey PDFs for analysis and research.

## Current Status (Nov 2025)

**Available PDFs:**
- `docs/2020/` — apega_salary_survey_2020.pdf (member report)
- `docs/2021/` — apega_salary_survey_2021.pdf (member report)
- `docs/2022/` — apega_salary_survey_2022.pdf (member report)
- `docs/2023/` — apega_salary_survey_2023.pdf (member report)
- `docs/2024/` — apega_salary_survey_2024.pdf (salary survey, scraped from Scribd)

**Unavailable:**
- `docs/2013-2019/` — PDFs could not be recovered (Wayback captures are corrupted HTML files, not valid PDFs). See `docs/2013-2019/README.txt` for details.

## Files & Scripts

### docs/
- `docs/YYYY/apega_salary_survey_YYYY.pdf` — Archived salary survey PDFs, organized by year.
- `docs/2013-2019/README.txt` — Note on why 2013–2019 PDFs are unavailable.

### scripts/
- `scripts/download_pdfs.py` — Download available PDFs (2020–2024) from APEGA and Internet Archive.
- `scripts/scrape_scribd_2024.py` — Scrape and convert Scribd documents to PDF (used for 2024).
- `scripts/parse_salary_tables.py` — Extract structured salary data from PDFs by career level, profession, organization counts, demographics.
- `scripts/forecast_salaries.py` — Forecast salary trends through 2030 using polynomial + linear regression.

### data/
- `data/salary_master.json` — Historical salary data extracted (2020, 2022-2023) by level, profession, organization stats, demographics.
- `data/salary_forecasts_2024_2030.json` — Projected median base salaries through 2030 for all career levels.
- `data/ANALYSIS_REPORT.md` — Comprehensive analysis report with findings, trends, and recommendations.

### outputs/
- `outputs/salary_trends_2020_2030.png` — 4-panel visualization (professional levels, management levels, career progression, growth rates).
- `outputs/participation_trends.png` — Organizational participation and professional composition trends.

### requirements.txt
Python dependencies (requests, beautifulsoup4, PyPDF2, selenium, pdfplumber, pandas, numpy, matplotlib, seaborn, scikit-learn, scipy).

## Usage

### 1. Create a Virtual Environment
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# or
source .venv/bin/activate     # macOS/Linux
```

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Download Available PDFs (2020–2024)
```bash
python scripts/download_pdfs.py
```

### 4. Extract Salary Data & Generate Forecasts
```bash
# Parse all PDFs and extract structured salary data
python scripts/parse_salary_tables.py

# Generate 2024-2030 forecasts and plots
python scripts/forecast_salaries.py
```

### 5. View Results
- Read analysis report: `data/ANALYSIS_REPORT.md`
- View salary plots: `outputs/salary_trends_2020_2030.png`, `outputs/participation_trends.png`
- Raw data: `data/salary_master.json`, `data/salary_forecasts_2024_2030.json`

---

## Analysis Highlights

### Historical Salary Growth (2020-2023)
- **Entry-level (P1):** +4.4% annual average
- **Senior Professional (P5):** +3.7% annual average  
- **Career progression:** P1→P5 spans **134% salary increase** (2023)

### 2024-2030 Forecasts
| Level | 2023 Actual | 2030 Forecast | Growth |
|-------|-------------|---------------|--------|
| P1 (Entry) | $78,614 | $125,216 | +59.3% |
| P5 (Expert) | $180,306 | $253,081 | +40.4% |
| M3 (Manager) | $186,744 | $323,403 | +73.2% |

### Key Trends
- **Participation:** 154 orgs (2022) → 212 orgs (2023) [+38%]
- **Professional mix:** Engineers 63% (2020) → 77% (2023)
- **Work arrangements:** 65% of orgs offer hybrid/remote (2023)
- **Entry-level growth:** Highest projected growth (+59%) reflects junior talent competition

## Notes

- **2013–2019 Recovery Attempt**: An exhaustive search was performed using Wayback CDX API, Google Cache, Archive.org, and academic repositories. All 2013–2019 Wayback snapshots contain HTML instead of PDF binaries, indicating they were never successfully archived as valid PDFs.
- **2024 Source**: The 2024 salary survey was scraped from Scribd (https://www.scribd.com/document/815516484/2024) as it was not available on the APEGA website.
- **Naming Convention**: All PDFs follow the standard `apega_salary_survey_YYYY.pdf` naming pattern.
- **Legal**: APEGA removed salary surveys from their public site in March 2025 citing Competition Act concerns. Archived copies are sourced from Internet Archive and Scribd. Please review APEGA's copyright notices and applicable laws before distributing or publicly using these reports.

## Project History

- Originally collected PDFs from APEGA website (2020–2023) and Internet Archive (Wayback).
- Removed corrupted 2013–2019 PDF files (HTML corruptions from Wayback captures).
- Added 2024 salary survey by scraping Scribd document and converting page images to PDF.
- Standardized file naming and folder structure for consistency.

