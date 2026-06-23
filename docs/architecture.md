# Project Architecture

```text
Excel Files
     │
     ▼
Loader (loader.py)
     │
     ▼
SQLite Database
(nifty100.db)
     │
     ▼
Validation Layer
(validator.py)
     │
     ▼
Manual Review
(manual_review.py)
     │
     ▼
Analytics Layer
(Future Sprint)
```

## Components

### Loader

Loads Excel files into SQLite.

### Validator

Checks data quality.

### Manual Review

Creates review reports for analyst verification.

### Analytics

Will generate business insights and dashboards.
```