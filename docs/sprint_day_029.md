# Sprint 5 — Day 29

## Task

NLP — Analysis Text Parser

## Objective

Build a structured NLP parsing pipeline for the supplied `analysis.xlsx` dataset and convert semi-structured financial growth text into machine-readable analytical records.

The parser also cross-validates extracted CAGR values against historical project datasets and flags material divergences for manual review.

---

## Files Implemented

### Core Parser

`src/nlp/parser.py`

### Generated Outputs

`output/analysis_parsed.csv`

`output/parse_failures.csv`

---

## Source Dataset

The parser processes:

`data/raw/analysis.xlsx`

The dataset contains the following analytical text fields:

- Compounded Sales Growth
- Compounded Profit Growth
- Stock Price CAGR
- ROE

---

## Parsing Logic

The parser extracts:

- Company ID
- Metric type
- Period
- Period label
- Percentage value
- Original raw text

The parser supports formats including:

- 10 Years
- 5 Years
- 3 Years
- 1 Year
- TTM
- Last Year

Positive, decimal and negative percentage values are supported.

---

## Regex Parsing

The primary parsing logic identifies year-period percentage patterns such as:

`10 Years: 21%`

`5 Years: 17.4%`

`1 Year: -2%`

Additional parsing logic handles:

- TTM percentages
- Last Year percentages
- Negative percentage values

---

## Parser Results

The final parser execution produced:

- Parsed records: 80
- Parse failures: 0

Metric distribution:

- Compounded Sales Growth: 20
- Compounded Profit Growth: 20
- Stock Price CAGR: 20
- ROE: 20

---

## Period Distribution

The parser successfully extracted:

- 10 Year: 20
- 5 Year: 20
- 3 Year: 20
- TTM: 10
- 1 Year: 5
- Last Year: 5

---

## CAGR Cross-Validation

Parsed CAGR values were cross-validated against available historical project data.

Historical P&L data was used to validate:

- Compounded Sales Growth
- Compounded Profit Growth

Historical stock-price data was used to validate:

- Stock Price CAGR

ROE values are treated as point-in-time financial ratios rather than CAGR metrics and therefore are not processed through the CAGR validation logic.

---

## Divergence Detection

A manual-review rule was implemented.

If the absolute difference between the parsed value and independently calculated value exceeds:

**5 percentage points**

the record is flagged as:

**MANUAL REVIEW**

---

## Validation Results

Final validation-status distribution:

- MATCH: 29
- MANUAL REVIEW: 9
- NOT VALIDATED: 42

Nine records exceeded the five-percentage-point divergence threshold and were retained for manual review.

The original parsed values were preserved rather than overwritten by calculated values.

---

## Data Integrity

The parser does not fabricate or silently replace financial values.

When historical data is insufficient for validation, the record remains available but is marked as:

`NOT VALIDATED`

When CAGR calculation is mathematically unsuitable because of non-positive base values, the pipeline can identify the case instead of forcing an invalid CAGR calculation.

Material differences between parsed and calculated values remain visible for review.

---

## Output Schema

The parsed analytical dataset contains fields including:

- company_id
- metric_type
- period_years
- period_label
- value_pct
- raw_text
- computed_value_pct
- divergence_pct_points
- calculation_status
- manual_review_flag
- validation_status
- review_reason

---

## Parse Failure Handling

Parsing failures are written to:

`output/parse_failures.csv`

The final execution produced:

**0 parse failures**

This confirms that all 80 analytical metric entries in the source dataset were successfully interpreted by the parser.

---

## Day 29 Outcome

The semi-structured financial analysis dataset has been converted into a structured analytical dataset suitable for downstream financial intelligence and reporting workflows.

The pipeline now supports:

- Financial text parsing
- Period extraction
- Percentage extraction
- Negative percentage parsing
- TTM parsing
- Last-year parsing
- Historical CAGR calculation
- Cross-validation
- Divergence detection
- Manual-review flagging
- Parse-failure logging

---

## Day 29 Status

**COMPLETE**