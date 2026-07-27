# Sprint Day 33 — PDF Company Tearsheet Template

## Sprint

Sprint 5 — Intelligence & Reports

## Day

Day 33

## Objective

Build and validate a reusable two-page PDF company tearsheet template for the Nifty 100 Financial Intelligence Platform.

The report combines company fundamentals, historical financial trends, balance-sheet composition, cash-flow intelligence, automated pros and cons, and capital-allocation signals into a concise analyst-facing report.

---

## Core Implementation

The PDF generator was implemented in:

`src/reports/tearsheet.py`

The module uses:

- ReportLab for PDF generation
- Matplotlib for financial charts
- SQLite as the primary structured data source
- Day 30 automated Pros/Cons output
- Day 31 Cash Flow Intelligence output

---

## Two-Page Tearsheet Layout

### Page 1 — Financial Overview

Page 1 includes:

- Company name
- Ticker
- Broad sector
- Sub-sector
- Six KPI tiles
- 10-year Revenue trend
- 10-year Net Profit trend
- ROE trend
- Current ROCE reference

The six KPI tiles include:

- Return on Equity
- ROCE
- Operating Profit Margin
- Debt-to-Equity
- Free Cash Flow
- P/E Ratio

---

## Page 2 — Financial Intelligence

Page 2 includes:

- Balance Sheet composition
- Latest-year Cash Flow chart
- Financial Strengths
- Financial Risks
- Capital Allocation classification
- Cash Flow Health classification

The Balance Sheet chart includes:

- Equity + Reserves
- Borrowings
- Other Liabilities

The Cash Flow chart includes:

- CFO
- CFI
- CFF
- Net Cash Flow

---

## Pros and Cons Integration

The tearsheet integrates:

`output/pros_cons_generated.csv`

The highest-confidence automated signals are selected for the report.

Signals are separated into:

- Financial Strengths
- Financial Risks

Text is rendered using wrapped ReportLab paragraph components to prevent overflow.

---

## Cash Flow Intelligence Integration

The tearsheet integrates:

`output/cashflow_intelligence.csv`

The latest company-level intelligence is used to display:

- Capital Allocation Pattern
- Cash Flow Health

---

## Historical ROCE Handling

The available project database contains historical ROE values but does not contain a complete historical ROCE series.

The company master contains the latest ROCE value.

Therefore:

- Historical ROE is plotted as the real time series.
- Current ROCE is displayed as a reference line.

Historical ROCE values were not fabricated.

---

## Day 33 Test Companies

The template was tested using five companies from different sectors:

- TCS
- HDFCBANK
- RELIANCE
- SUNPHARMA
- TATASTEEL

Generated test reports were stored in:

`reports/tearsheets/day33_test/`

---

## Automated Validation Results

| Company | PDF Generated | Status |
| --- | --- | --- |
| TCS | Yes | PASS |
| HDFCBANK | Yes | PASS |
| RELIANCE | Yes | PASS |
| SUNPHARMA | Yes | PASS |
| TATASTEEL | Yes | PASS |

Total companies tested: 5

PDFs generated: 5

Passed: 5

Failed: 0

Result:

**DAY 33 VALIDATION PASSED**

---

## Visual QA

The TCS report was manually inspected.

### Page 1

Verified:

- Header alignment
- KPI tile alignment
- Chart readability
- Axis labels
- Revenue and Net Profit chart layout
- ROE/ROCE chart layout
- Footer rendering
- No overflow

### Page 2

Verified:

- Balance Sheet chart
- Cash Flow chart
- Pros and Cons wrapping
- Capital Allocation badge
- Cash Flow Health badge
- Footer rendering
- No overflow
- No unintended third page

---

## Data Integrity

The report generator does not fabricate unavailable financial values.

Important safeguards include:

- Embedded-header repair for raw database tables
- Missing-data handling
- Historical financial-year sorting
- No fabricated ROCE history
- Existing analytical outputs reused rather than recalculated inconsistently
- Wrapped report text
- Controlled two-page layout

---

## Day 33 Output

Primary implementation:

`src/reports/tearsheet.py`

Test reports:

`reports/tearsheets/day33_test/`

---

## Day 33 Outcome

A reusable production-style two-page company tearsheet template is now available.

The template successfully integrates:

- Company metadata
- Financial ratios
- Historical P&L trends
- Balance-sheet history
- Cash-flow history
- Automated Pros/Cons
- Capital Allocation Intelligence
- Cash Flow Health

The template is ready for Day 34 batch generation across the official company universe.

---

## Day 33 Status

**COMPLETE**