# Sprint 4 Review — Interactive Financial Intelligence Dashboard

## Sprint Duration

Days 22–28

## Sprint Objective

The objective of Sprint 4 was to transform the analytical engines
developed during the earlier sprints into an interactive financial
intelligence dashboard for the Nifty 100 universe.

The sprint focused on integrating company fundamentals, financial
ratios, peer comparisons, trend analysis, sector intelligence,
capital-allocation analysis and annual-report access into a unified
Streamlit application.

---

## Deliverables Completed

### 1. Dashboard Architecture

A multi-page Streamlit dashboard was implemented with the following
pages:

- Home
- Company Profile
- Financial Screener
- Peer Comparison
- Financial Trends
- Sector Analysis
- Capital Allocation
- Annual Reports

The pages share the same underlying SQLite financial database.

---

## 2. Home Dashboard

The home page provides a portfolio-level overview of the Nifty 100
universe.

Key functionality includes:

- Financial KPI summary
- Sector distribution
- Total company count
- ROE and valuation statistics
- Top-company quality overview

---

## 3. Company Profile

A detailed company-level analytical page was implemented.

Functionality includes:

- Company search
- Company metadata
- Sector and sub-sector information
- Financial KPI snapshot
- Revenue trend
- Net-profit trend
- ROE trend
- ROCE reference
- Financial strengths
- Financial risk indicators

---

## 4. Financial Screener

An interactive financial screener was implemented using the analytical
metrics developed in earlier sprints.

Supported filters include:

- ROE
- Debt / Equity
- Free Cash Flow
- Revenue CAGR
- PAT CAGR
- Operating Margin
- P/E
- P/B
- Dividend Yield
- Interest Coverage
- Sector

Preset screening strategies were also integrated.

Screener results can be exported to CSV.

---

## 5. Peer Comparison Dashboard

The peer-comparison page integrates the Sprint 3 peer-group engine.

Features include:

- Peer-group selector
- Company selector
- Benchmark identification
- Peer-relative percentile radar chart
- Financial KPI comparison table
- Company peer snapshot

---

## 6. Financial Trend Analysis

A historical trend-analysis page was developed using the supplied
profit-and-loss dataset.

Features include:

- Financial-year selector
- Revenue rankings
- Growth leaders
- Net-profit growth leaders
- Company trend explorer
- Revenue and profit history
- Year-over-year growth calculation
- Financial momentum analysis
- Trend dataset export

The raw profit-and-loss table structure was repaired dynamically before
analysis because the source dataset contained embedded headers.

---

## 7. Sector Analysis

A dedicated sector-intelligence page was created.

Features include:

- Sector selector
- Company count
- Median revenue
- Median ROE
- Median market capitalization
- Revenue vs ROE bubble chart
- Sector median KPI comparison
- Company-level sector table
- CSV export

---

## 8. Capital Allocation Map

The Sprint 2 cash-flow classification engine was integrated into the
dashboard.

The latest allocation dataset covers all 92 official companies.

The dashboard includes eight capital-allocation patterns:

- Shareholder Returns
- Reinvestor
- Mixed
- Growth Funded by Debt
- Liquidating Assets
- Other
- Distress Signal
- Pre-Revenue

Features include:

- Capital-allocation treemap
- Pattern distribution chart
- Pattern selector
- Company classification table
- CSV export

One company, ATGL, had no cash-flow records in the supplied cash-flow
dataset. It was retained transparently in the analytical universe under
the data-availability handling logic rather than assigning fabricated
cash-flow values.

---

## 9. Annual Reports Library

The documents dataset was integrated into the dashboard.

Features include:

- Company search
- Annual-report year history
- Direct annual-report links
- PDF access
- Report index export

The documents source required header repair because the actual column
headers were stored in the first data row.

Annual-report links were verified to open successfully.

---

## Data Integrity

The dashboard uses the supplied Nifty 100 project datasets and the
SQLite analytical database created during the earlier sprints.

No missing financial values were manually fabricated.

Special data-availability cases were handled explicitly in the
application.

---

## Technical Challenges Resolved

During Sprint 4 several data-integration issues were identified and
resolved:

1. Embedded spreadsheet headers in imported SQLite tables.
2. Inconsistent company coverage between datasets.
3. Missing cash-flow history for ATGL.
4. Capital-allocation coverage reconciliation.
5. Historical year-format differences.
6. Annual-report URL column detection.
7. Streamlit compatibility issues.
8. Dashboard joins across companies, sectors and financial data.

---

## Sprint Outcome

Sprint 4 successfully transformed the financial analytics pipeline into
a working interactive financial intelligence platform.

The dashboard now provides:

- Company analysis
- Financial screening
- Peer benchmarking
- Historical trend analysis
- Sector intelligence
- Capital allocation analysis
- Annual-report access

This provides the user-facing analytical foundation required for the
remaining project sprints.

---

## Sprint Status

**Sprint 4: COMPLETE**