# apega-salary-survey-analysis

A project to collect and archive APEGA Salary Survey PDFs for analysis and research. APEGA discontinued the salary survery early 2025.

## Current Status (Nov 2025)

**Available PDFs:**
- `docs/2020/` — apega_salary_survey_2020.pdf (member report)
- `docs/2021/` — apega_salary_survey_2021.pdf (member report, different format)
- `docs/2022/` — apega_salary_survey_2022.pdf (member report)
- `docs/2023/` — apega_salary_survey_2023.pdf (member report)
- `docs/2024/` — apega_salary_survey_2024.pdf (salary survey, scraped from Scribd)

**Unavailable:**
- `docs/2013-2019/` — PDFs could not be recovered (Wayback captures are corrupted HTML files, not valid PDFs). See `docs/2013-2019/README.txt` for details.

## Files & Scripts

### docs/
- `docs/YYYY/apega_salary_survey_YYYY.pdf` — Archived salary survey PDFs, organized by year.
- `docs/2013-2019/README.txt` — Note on why 2013–2019 PDFs are unavailable.

### tools/
- `responsibility-level-tool.xlsm` — Tool to assess responsibilty level.

### requirements.txt
Python dependencies (requests, beautifulsoup4, PyPDF2, selenium, pdfplumber, pandas, numpy, matplotlib, seaborn, scikit-learn, scipy).

Key findings
- Entry-level (P1) — 2023 median base: $78,614; 2030 forecast: $110,025 (approx. +40%).
- Senior professional (P5) — 2023 median base: $180,306; 2030 forecast: $293,791 (substantial projected rise driven by model ensemble).
- Management (example M3) — 2023 median base: $186,744; 2030 forecast: $388,773 (group-harmonized forecasts applied to smooth anomalies).
- Participation trend: survey participation increased significantly between 2022 and 2023 (organization counts rose in the available data).

Methodology (short)
- Historical series are extracted from the consolidated master dataset and projected using a simple ensemble: linear regression + degree-2 polynomial; the two model predictions are averaged for robustness.
- Post-processing safeguards: monotonicity enforcement and group-level harmonization prevent artifacts (flat/declining forecasts) for senior levels when peer-level trends are consistently upward.

Data provenance & important notes
- The repository contains manually validated extracts for years with PDF extraction difficulties (notably 2021 and 2024). Some entries were adjusted to remove clear transcription errors prior to forecasting.
- `GEO` (geoscientist) series are available but incomplete; forecasts emphasize `ENG` where data is sufficient.
- Certain visual outputs use estimated values where the raw source did not include explicit fields (for example, total cash compensation may be estimated as base * (1 + assumed bonus%)). Any such estimation is documented in the script that produces the output.
- Legal/ethical: archived copies were collected from public archives and third-party hosts. Verify licensing and distribution permissions before sharing derived data beyond internal analysis.