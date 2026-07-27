# Sprint 5 — Day 31

## Task

Cash Flow Intelligence Module

## Objective

Build a company-year cash flow intelligence engine that combines cash-flow statements, profit-and-loss data, financial ratios, and company master data into structured analytical signals.

The module evaluates cash generation quality, capital expenditure intensity, capital allocation behaviour, distress signals, and overall cash-flow health.

---

## Files Implemented

### Core Engine

`src/analytics/cashflow_intelligence.py`

### Existing KPI Module Reused

`src/analytics/cashflow_kpis.py`

### Generated Output

`output/cashflow_intelligence.csv`

---

## Data Sources

The engine integrates the following SQLite tables:

- `cashflow`
- `profitandloss`
- `financial_ratios`
- `companies`

The raw cash-flow and profit-and-loss tables contain embedded headers in the first data row.

These headers are repaired dynamically before calculations are performed.

---

## Official Universe Reconciliation

The raw financial datasets contain companies outside the official project universe.

The engine explicitly reconciles all source datasets against the official `companies` table before performing analysis.

### Official Company Universe

92 companies

### Raw Cash Flow Companies

100 companies

### Raw P&L Companies

100 companies

### Raw Financial Ratio Companies

92 companies

### Excluded Non-Official Cash Flow Companies

- AGTL
- ULTRACEMCO
- UNIONBANK
- UNITDSPR
- VBL
- VEDL
- WIPRO
- ZOMATO
- ZYDUSLIFE

### Official Companies Missing Cash Flow Data

- ATGL

### Official Companies Missing Financial Ratio Data

- ATGL
- SBIN

No financial records were remapped or fabricated to force complete coverage.

---

## Final Official-Universe Coverage

After reconciliation:

- Official companies: 92
- Cash-flow companies: 91
- P&L companies: 92
- Financial-ratio companies: 90
- Cash-flow intelligence records: 1,056

---

## Free Cash Flow

Free Cash Flow is calculated using:

`FCF = CFO + CFI`

where:

- CFO = Cash Flow from Operating Activities
- CFI = Cash Flow from Investing Activities

Negative FCF is retained as a valid analytical value.

---

## CFO Quality

CFO quality compares operating cash generation against reported profit.

The engine produces:

- `cfo_quality_score`
- `cfo_quality_label`

Observed distribution:

- High Quality: 609
- Moderate: 192
- Accrual Risk: 252
- Not Available: 3

---

## CapEx Intensity

CapEx intensity measures investment intensity relative to sales.

Generated labels include:

- Asset Light
- Moderate
- Capital Intensive
- Not Available

Observed distribution:

- Capital Intensive: 495
- Asset Light: 289
- Moderate: 269
- Not Available: 3

---

## FCF Conversion

The module calculates Free Cash Flow conversion relative to operating profit.

Available values:

- 1,041 / 1,056 records

---

## Capital Allocation Classification

CFO, CFI, and CFF sign patterns are used to classify company-year capital allocation behaviour.

Observed patterns include:

- Shareholder Returns
- Mixed
- Reinvestor
- Growth Funded by Debt
- Liquidating Assets
- Distress Signal
- Other
- Pre-Revenue
- Cash Accumulator
- Not Available

---

## Distress Intelligence

The engine implements multiple cash-flow distress signals.

### Signals

- Negative CFO
- Financing dependence
- Three-year negative FCF streak
- Distress capital-allocation pattern
- Overall distress flag

### Final Counts

- Three-year negative FCF: 95
- Negative CFO: 161
- Financing dependent: 137
- Capital-allocation distress: 143
- Overall distress: 189

---

## Cash Flow Health Score

A cash-flow health score from 0 to 100 is generated using:

- CFO quality
- FCF direction
- Capital allocation behaviour
- Persistent negative FCF
- Financing dependence

The score is converted into four labels:

- Strong
- Healthy
- Watch
- Distress

Final distribution:

- Strong: 591
- Healthy: 83
- Watch: 181
- Distress: 201

---

## Data Quality Controls

The engine performs the following safeguards:

- Embedded-header repair
- Company ticker normalization
- Financial-year normalization
- Duplicate company-year removal
- Official universe filtering
- Missing-data transparency
- No ticker remapping
- No fabricated financial values
- Health-score range validation
- Company-year duplicate validation

---

## Validation Results

Final validation:

- Intelligence records: 1,056
- Companies covered: 91
- Official companies: 92
- Missing cash-flow company: ATGL
- Duplicate company-year records: 0
- Invalid health scores: 0

Result:

**DAY 31 VALIDATION PASSED**

---

## Day 31 Outcome

The project now contains a complete company-year Cash Flow Intelligence engine capable of evaluating:

- Cash-generation quality
- CapEx intensity
- Free Cash Flow
- FCF conversion
- Capital-allocation behaviour
- Persistent cash-flow weakness
- Financing dependence
- Distress patterns
- Overall cash-flow health

The output is ready for Day 32 workbook generation and reporting.

---

## Day 31 Status

**COMPLETE**