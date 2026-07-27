# Sprint Day 35 — Portfolio Summary PDF & Sprint Review

## Sprint

Sprint 5 — Intelligence & Reports

## Day

Day 35

## Objective

Generate the final portfolio-level summary report for the complete official company universe and complete the Sprint 5 reporting workflow.

The Portfolio Summary PDF provides a compact one-page analytical snapshot for every official company, ordered alphabetically by ticker.

---

## Core Implementation

The portfolio reporting engine was implemented in:

`src/reports/portfolio_report.py`

Generated output:

`src/reports/portfolio/portfolio_summary.pdf`

---

## Company Universe

Official companies processed:

**92**

The report generator processes companies alphabetically by ticker.

Validation confirmed:

- Companies included: 92
- Duplicate companies: 0
- Alphabetical ticker order: True

---

## Portfolio Report Structure

Each company receives one analytical summary page.

Each page contains:

- Company name
- Company ticker
- Broad sector
- Sub-sector
- Six KPI cards
- KPI trend indicators
- Capital Allocation classification
- Cash Flow Health classification
- Trend interpretation legend

---

## Six KPI Snapshot

The Portfolio Summary displays:

1. Return on Equity
2. ROCE
3. Operating Profit Margin
4. Debt-to-Equity
5. Free Cash Flow
6. P/E Ratio

---

## Trend Intelligence

Each KPI compares the latest available observation against the immediately preceding observation.

Trend indicators are classified as:

- ▲ Improved
- ▼ Declined
- → Flat
- — No comparison available

A change is treated as flat when the absolute movement is within 2%.

For metrics where lower values are preferable, such as Debt-to-Equity, the improvement direction is handled accordingly.

---

## ROCE Handling

The current project datasets provide current ROCE values but do not provide a complete historical ROCE time series.

Therefore:

- Current ROCE is displayed.
- No historical ROCE trend is fabricated.
- ROCE is marked as a current-only metric where historical comparison is unavailable.

---

## Cash Flow Intelligence Integration

The report integrates:

`output/cashflow_intelligence.csv`

The latest available company intelligence provides:

- Capital Allocation
- Cash Flow Health

One official company does not have valid cash-flow history in the supplied source dataset.

Therefore:

- Missing Capital Allocation: 1
- Missing Cash Flow Health: 1

Missing values remain explicitly marked as unavailable rather than being fabricated.

---

## Validation Results

Final automated validation:

| Validation Check | Result |
| --- | ---: |
| PDF Created | Yes |
| Companies Included | 92 |
| Duplicate Companies | 0 |
| Alphabetical Ticker Order | True |
| Missing Capital Allocation | 1 |
| Missing Cash Flow Health | 1 |
| Portfolio Validation | PASS |

The generated PDF size was:

**194,709 bytes**

---

## Data Integrity

The Portfolio Summary preserves the project's existing data-integrity rules.

Safeguards include:

- Official company universe only
- No duplicate company pages
- No fabricated historical ROCE
- No fabricated cash-flow classifications
- Missing values explicitly shown as unavailable
- Latest and previous periods selected chronologically
- Metric-specific trend-direction handling

---

## Day 35 Output

Primary implementation:

`src/reports/portfolio_report.py`

Generated portfolio report:

`src/reports/portfolio/portfolio_summary.pdf`

---

## Day 35 Outcome

The project now contains a complete portfolio-level reporting layer covering all 92 official companies.

The final Sprint 5 reporting stack includes:

- NLP financial-text parsing
- Automated Pros and Cons
- Cash Flow Intelligence
- Cash Flow Excel reporting
- Two-page company tearsheets
- Full-universe tearsheet batch generation
- Sector reports
- Portfolio Summary PDF

---

## Day 35 Status

**COMPLETE**