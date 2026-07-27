# Sprint 5 — Day 30

## Task

NLP — Auto Pros/Cons Generator

## Objective

Develop an automated rule-based financial intelligence engine that converts structured historical company fundamentals into concise company-level strengths and risk observations.

The engine generates pros and cons for the complete official company universe using financial ratios, profit-and-loss history, balance-sheet history, valuation data and company-level fundamentals.

---

## Files Implemented

### Core Generator

`src/nlp/pros_cons_generator.py`

### Data Inspection Utility

`src/nlp/inspect_pros_cons_data.py`

### Generated Output

`output/pros_cons_generated.csv`

---

## Data Sources

The generator integrates data from the project's SQLite analytical database.

Primary tables used include:

- `companies`
- `financial_ratios`
- `market_cap`
- `profitandloss`
- `balancesheet`

Historical spreadsheet-backed tables containing embedded headers are repaired dynamically before analysis.

---

## Rule Engine

The generator implements:

- 12 Pro rules
- 12 Con rules

Each rule evaluates a specific financial condition and generates a human-readable analytical signal when the condition is satisfied.

---

## Pro Rules

The following financial-strength signals were implemented:

1. Sustained ROE above 20%
2. Positive free cash flow over multiple years
3. Debt-free balance sheet
4. Revenue CAGR above 15%
5. Operating margin above 25%
6. PAT CAGR above 20%
7. Strong interest coverage / debt-free status
8. Dividend yield above 2% supported by positive FCF
9. EPS CAGR above 15%
10. Improving ROE trend
11. Revenue/profit growth relationship
12. Asset growth accompanied by declining debt

---

## Con Rules

The following financial-risk signals were implemented:

1. High debt-to-equity for non-financial companies
2. Negative free cash flow for multiple consecutive years
3. Declining operating margins
4. Latest-year net loss
5. Multi-year revenue contraction
6. Weak interest coverage
7. Dividend payout above 100%
8. Rising debt-to-equity trend
9. Declining EPS trend
10. ROCE below 10%
11. High debt relative to estimated EBITDA
12. Revenue CAGR below 5%

---

## Confidence Scoring

Every generated signal receives a confidence score between:

**0–100%**

Only signals with confidence:

**> 60%**

are retained in the final output.

The final generated dataset contained no signals at or below the minimum threshold.

---

## Historical Trend Analysis

The engine supports multi-year financial analysis rather than relying only on the latest financial record.

Historical calculations include:

- Revenue CAGR
- PAT CAGR
- EPS CAGR
- ROE trends
- Debt-to-equity trends
- Operating-margin trends
- Free-cash-flow consistency
- Asset-growth trends
- Borrowing trends

Historical year strings are normalized before chronological analysis.

---

## Embedded Header Repair

The raw profit-and-loss and balance-sheet tables contain their actual field names inside the first data row.

The generator dynamically repairs these tables before performing financial calculations.

This exposes fields including:

- Sales
- Net Profit
- EPS
- Operating Profit
- Depreciation
- Borrowings
- Total Assets

---

## EBITDA Handling

The available `ev_ebitda` field represents a valuation multiple and therefore is not treated as EBITDA.

For leverage analysis, estimated EBITDA is derived from available operating-profit and depreciation data.

Where a reliable cash-equivalent field is unavailable, total debt is used conservatively rather than fabricating a cash balance.

---

## Financial-Sector Handling

Debt-to-equity thresholds designed for ordinary operating companies are not blindly applied to financial-sector companies.

Financial-sector identification is used to reduce inappropriate leverage warnings for businesses where debt forms part of the operating model.

---

## Coverage Fallback

The acceptance criteria require every company to receive at least:

- One Pro
- One Con

If no primary rule of a particular type triggers, a conservative fallback observation is generated.

Fallback observations are designed as monitoring or data-availability signals rather than fabricated financial conclusions.

---

## Final Results

The final generator execution produced:

- Official companies: 92
- Companies with Pros: 92
- Companies with Cons: 92
- Total signals: 495
- Pro signals: 353
- Con signals: 142

Confidence range:

- Minimum: 61.0%
- Maximum: 100.0%

Missing Pro coverage:

**None**

Missing Con coverage:

**None**

Invalid confidence records:

**0**

---

## Rule Coverage

All 12 primary Pro rules generated at least one signal.

All 12 primary Con rules generated at least one signal.

Fallback usage:

- Pro fallback: 2
- Con fallback: 38

This demonstrates that the complete primary rule engine executed successfully while fallback logic ensured complete company coverage.

---

## Data Integrity

The generator does not manually fabricate missing financial values.

Important safeguards include:

- Missing values remain missing until a valid rule can operate on them.
- Historical observations are sorted chronologically.
- Duplicate year records are resolved before trend analysis.
- CAGR calculations reject invalid non-positive base values.
- Financial-sector leverage is handled separately.
- EV/EBITDA is not incorrectly treated as EBITDA.
- Confidence thresholds are enforced before output.
- Fallback signals avoid pretending unavailable financial evidence exists.

---

## Output Schema

`pros_cons_generated.csv` contains:

- `company_id`
- `type`
- `rule_id`
- `text`
- `confidence_pct`

The `type` field identifies each observation as:

- `pro`
- `con`

---

## Validation Results

The final validation produced:

**Official companies: 92**

**Companies with pros: 92**

**Companies with cons: 92**

**Missing pros: None**

**Missing cons: None**

**Invalid confidence rows: 0**

Therefore:

**DAY 30 VALIDATION PASSED — EVERY COMPANY HAS AT LEAST ONE PRO AND ONE CON**

---

## Day 30 Outcome

The project now contains an automated financial Pros/Cons generation engine capable of converting historical structured financial data into explainable company-level financial intelligence.

The generated signals can subsequently be integrated into company reports and downstream NLP/report-generation workflows.

---

## Day 30 Status

**COMPLETE**