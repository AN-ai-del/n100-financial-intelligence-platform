# Sprint 6 — Day 39
# FastAPI Company Data Endpoints

## Objective

Implemented the company-data API layer for the Nifty 100 Financial Intelligence Platform.

The Day 39 endpoints provide:

- Company listing
- Company search
- Sector filtering
- Market-cap filtering
- Full company profile
- Profit and Loss history
- Balance Sheet history
- Cash Flow history
- Financial ratio history
- Single-year ratio filtering
- Company tearsheet download handling
- Input validation
- HTTP 404 and HTTP 400 error handling

---

# Day 39 Requirements

The implementation covers the following API routes:

```http
GET /api/v1/companies
```

```http
GET /api/v1/companies/{ticker}
```

```http
GET /api/v1/companies/{ticker}/pl
```

```http
GET /api/v1/companies/{ticker}/bs
```

```http
GET /api/v1/companies/{ticker}/cashflow
```

```http
GET /api/v1/companies/{ticker}/ratios
```

```http
GET /api/v1/companies/{ticker}/tearsheet
```

---

# Source File

```text
src/api/routers/companies.py
```

---

# Company List Endpoint

## Route

```http
GET /api/v1/companies
```

## Purpose

Returns all official companies with normalized company metadata.

## Response Fields

- Company ID
- Company name
- Broad sector
- Sub-sector
- Market-cap category
- Latest ROE
- ROCE

## Validation Result

```text
Company count: 92
```

---

# Company Search

## Ticker Search

Example:

```http
GET /api/v1/companies?search=TCS
```

Result:

```json
{
  "count": 1,
  "companies": [
    {
      "id": "TCS",
      "company_name": "Tata Consultancy Services Ltd",
      "broad_sector": "Information Technology",
      "sub_sector": "IT Services",
      "market_cap_category": "Large Cap",
      "roe_pct": 50.94,
      "roce_pct": 64.3
    }
  ]
}
```

---

## Partial Name Search

Example:

```http
GET /api/v1/companies?search=tata
```

Returned matching companies including:

- Tata Consumer Products
- Tata Motors
- Tata Power
- Tata Steel
- Tata Consultancy Services

---

# Sector Filter

## Route Example

```http
GET /api/v1/companies?sector=Information%20Technology
```

## Validation Result

The endpoint returned 5 Information Technology companies:

- HCLTECH
- INFY
- LTIM
- TCS
- TECHM

All returned records matched the requested broad sector.

---

# Market-Cap Filter

The company list endpoint supports:

```http
GET /api/v1/companies?market_cap_category=Large%20Cap
```

Filtering is case-insensitive.

---

# Full Company Profile

## Route

```http
GET /api/v1/companies/{ticker}
```

## Example

```http
GET /api/v1/companies/TCS
```

## Response Sections

- Company ID
- Normalized company metadata
- Original company-master fields
- Sector metadata
- Latest financial KPIs

## Validation Result

```text
HTTP 200
```

---

# Invalid Company Handling

## Example

```http
GET /api/v1/companies/INVALID
```

## Response

```json
{
  "detail": "Company 'INVALID' was not found."
}
```

## Status

```text
HTTP 404
```

---

# Profit and Loss History

## Route

```http
GET /api/v1/companies/{ticker}/pl
```

## Example

```http
GET /api/v1/companies/TCS/pl
```

## Result

```text
12 yearly records
```

---

## Date Filter

```http
GET /api/v1/companies/TCS/pl?from_year=2019-03&to_year=2024-03
```

## Result

```text
6 yearly records
```

The returned records covered:

- 2019-03
- 2020-03
- 2021-03
- 2022-03
- 2023-03
- 2024-03

---

# Balance Sheet History

## Route

```http
GET /api/v1/companies/{ticker}/bs
```

## Example

```http
GET /api/v1/companies/TCS/bs?from_year=2019-03&to_year=2024-03
```

## Result

```text
6 yearly records
```

---

# Cash Flow History

## Route

```http
GET /api/v1/companies/{ticker}/cashflow
```

## Example

```http
GET /api/v1/companies/TCS/cashflow?from_year=2019-03&to_year=2024-03
```

## Result

```text
6 yearly records
```

Duplicate source rows were automatically removed.

The final response contains one record for each year:

- 2019-03
- 2020-03
- 2021-03
- 2022-03
- 2023-03
- 2024-03

---

# Financial Ratio History

## Route

```http
GET /api/v1/companies/{ticker}/ratios
```

## Example

```http
GET /api/v1/companies/TCS/ratios
```

## Result

```text
12 yearly records
```

This satisfies the requirement that TCS returns at least 10 years of ratio history.

---

# Single-Year Ratio Filter

## Example

```http
GET /api/v1/companies/TCS/ratios?year=2024-03
```

## Result

```text
1 ratio record
```

---

# Year Validation

The API accepts year values only in:

```text
YYYY-MM
```

## Invalid Example

```http
GET /api/v1/companies/TCS/ratios?year=2024
```

## Response

```json
{
  "detail": "year must use YYYY-MM format."
}
```

## Status

```text
HTTP 400
```

---

# Date-Range Validation

The API validates:

- `from_year`
- `to_year`
- Correct `YYYY-MM` format
- `from_year` must not be later than `to_year`

Invalid parameters return:

```text
HTTP 400
```

---

# Tearsheets

## Route

```http
GET /api/v1/companies/{ticker}/tearsheet
```

The endpoint searches for a generated company PDF in:

```text
reports/tearsheets/
```

```text
reports/
```

```text
src/reports/
```

When a PDF exists, the API returns it using:

```text
application/pdf
```

When a valid company has no generated tearsheet, the API returns:

```json
{
  "detail": "No pre-generated tearsheet was found for 'TCS'."
}
```

with:

```text
HTTP 404
```

---

# Data Normalization

The API normalizes:

- Company tickers to uppercase
- Column names to snake_case
- Null values
- Numeric values
- Financial-year values
- Embedded source-table headers

Supported year formats include:

```text
Mar 2024
Mar-24
FY24
2024
2024-03
```

These values are converted into:

```text
YYYY-MM
```

---

# Source Table Compatibility

The API supports both:

1. Standard SQLite tables with physical columns such as:

```text
company_id
year
sales
net_profit
```

2. Imported tables where:

- SQLite columns contain generic names
- The first data row contains the real headers

This allows the API to read the current project database without changing the source data.

---

# Duplicate Handling

Financial histories are deduplicated by normalized year.

When duplicate records exist, the API keeps:

1. The record with more populated fields
2. The record with the latest database ID when completeness is equal

This removed duplicate cash-flow records without deleting source rows.

---

# Error Handling

## Invalid Ticker

```text
HTTP 404
```

## Missing Required Table

```text
HTTP 503
```

## Invalid Year Format

```text
HTTP 400
```

## Reversed Date Range

```text
HTTP 400
```

## Missing Tearsheet

```text
HTTP 404
```

---

# Swagger Documentation

All seven company endpoints appear under the `Companies` section in:

```text
http://127.0.0.1:8000/docs
```

Registered endpoints:

```text
GET /api/v1/companies
GET /api/v1/companies/{ticker}
GET /api/v1/companies/{ticker}/pl
GET /api/v1/companies/{ticker}/bs
GET /api/v1/companies/{ticker}/cashflow
GET /api/v1/companies/{ticker}/ratios
GET /api/v1/companies/{ticker}/tearsheet
```

---

# Validation Results

| Validation Check | Result |
|---|---|
| Company router imports | PASS |
| Seven routes registered | PASS |
| Company list returns 92 companies | PASS |
| Ticker search works | PASS |
| Partial-name search works | PASS |
| Sector filter works | PASS |
| Sector metadata populated | PASS |
| Market-cap category populated | PASS |
| Latest ROE populated | PASS |
| Full TCS profile returns HTTP 200 | PASS |
| Invalid ticker returns HTTP 404 | PASS |
| TCS ratio history returns 12 years | PASS |
| Single-year ratio filter works | PASS |
| Invalid year returns HTTP 400 | PASS |
| P&L history works | PASS |
| Balance Sheet history works | PASS |
| Cash Flow history works | PASS |
| Duplicate history rows removed | PASS |
| Date-range filtering works | PASS |
| Missing tearsheet handling works | PASS |
| Swagger documentation updated | PASS |

---

# Files Modified

```text
src/api/routers/companies.py
```

---

# Files Added

```text
docs/sprint_day_039.md
```

---

# Skills Demonstrated

- FastAPI Routing
- REST API Design
- SQLite Queries
- Dynamic Schema Handling
- JSON Serialization
- Query Parameters
- API Filtering
- Input Validation
- Financial-Year Normalization
- Duplicate Detection
- HTTP Error Handling
- File Downloads
- Swagger Documentation
- Financial Data APIs

---

# Result

Successfully implemented and validated the complete company-data API layer for the Nifty 100 Financial Intelligence Platform.

The API now provides normalized company metadata, sector-aware filtering, company profiles, financial-statement histories, ratio histories, date filtering, duplicate removal, and tearsheet download handling.

---

# Day 39 Status

```text
COMPLETE
```