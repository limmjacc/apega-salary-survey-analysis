# apega-salary-survey-analysis
A project to collect APEGA Salary Survey PDFs (archival) and build analysis over time.

Docs and scripts added:

- `docs/` — contains downloaded APEGA Salary Survey PDFs (archived copies via Wayback where APEGA removed them). See `docs/index.md` for an index and checksums.
- `scripts/download_pdfs.py` — Python script to try downloading the PDFs from APEGA and the Internet Archive (Wayback) and save them into `docs/`.

How to fetch

1. Install Python 3.10+ and create a virtual environment.
2. Install the `requests` package: `pip install requests`.
3. Run `python scripts/download_pdfs.py` to download available PDFs to `docs/`.

Legal note: APEGA removed the Salary Survey from their public site in early 2025 and stated legal concerns. The script fetches archived copies from the Internet Archive; please review APEGA's copyright notices and the Competition Act before distributing or using these reports publicly.
