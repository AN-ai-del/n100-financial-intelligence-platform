# N100 Financial Intelligence Platform

## Dataset Overview

| File | Description |
|--------|------------|
| companies.xlsx | Company master information |
| balancesheet.xlsx | Balance sheet data |
| profitandloss.xlsx | Profit & Loss statements |
| cashflow.xlsx | Cash flow statements |
| analysis.xlsx | Financial analysis metrics |
| documents.xlsx | Company documents |
| prosandcons.xlsx | Pros and cons information |
| financial_ratios.xlsx | Financial ratio data |
| peer_groups.xlsx | Industry peer comparison |
| sectors.xlsx | Sector classification |
| market_cap.xlsx | Market capitalization data |
| stock_prices.xlsx | Historical stock prices |

## Storage

All Excel datasets are loaded into SQLite database:

db/nifty100.db

## Validation

Data quality checks include:

- Missing value checks
- Duplicate checks
- Row count validation
- Manual review reporting