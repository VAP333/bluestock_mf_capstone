# Bluestock Fintech - Mutual Fund Analytics Capstone

Capstone project for the Data Analyst Internship at Bluestock Fintech.
Building a mutual fund analytics platform using public AMFI data.

## Project Structure

```
bluestock_mf_capstone/
    data/
        raw/            - original CSVs and live NAV fetches
        processed/      - cleaned data (day 2 onwards)
        db/             - sqlite database (day 2 onwards)
    notebooks/          - jupyter notebooks for each day
    scripts/            - python scripts
    sql/                - schema and queries
    dashboard/          - power bi file
    reports/            - final report and presentation
    requirements.txt
    README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Running Day 1 scripts

```bash
python scripts/data_ingestion.py
python scripts/live_nav_fetch.py
```

`live_nav_fetch.py` hits the mfapi.in API to pull historical NAV for 6 schemes.
If the API is blocked it falls back to the provided nav_history CSV.

## Data Sources

- AMFI India (amfiindia.com) - NAV, AUM, SIP data
- mfapi.in - historical NAV JSON API
- NSE/BSE - benchmark index prices

10 datasets provided, covering 40 fund schemes, ~87K rows total.

## Progress

| Day | Task | Status |
|-----|------|--------|
| 1 | Data ingestion + folder setup | done |
| 2 | Data cleaning + SQL database | pending |
| 3 | EDA | pending |
| 4 | Performance analytics | pending |
| 5 | Dashboard | pending |
| 6 | Advanced analytics | pending |
| 7 | Final report | pending |
