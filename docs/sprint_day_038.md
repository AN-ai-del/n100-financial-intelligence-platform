# Sprint 6 — Day 38
# FastAPI Server Scaffold

## Objective

Created the REST API foundation for the Nifty 100 Financial Intelligence Platform using FastAPI.

The API scaffold provides:

- Central FastAPI application
- SQLite database integration
- Modular router architecture
- CORS middleware
- Request logging middleware
- Health and readiness endpoints
- Automatic Swagger documentation
- API versioning
- Runtime and database diagnostics

---

# Day 38 Requirements

The Day 38 implementation covers:

- `src/api/main.py`
- SQLite connection utilities
- CORS support for internal usage
- Request method, route, status and response-time logging
- Separate router modules
- `/api/v1` route prefix
- Health endpoint
- Database row-count reporting
- API uptime reporting
- API version reporting
- Swagger/OpenAPI documentation

---

# API Directory Structure

```text
src/
└── api/
    ├── __init__.py
    ├── database.py
    ├── main.py
    └── routers/
        ├── __init__.py
        ├── companies.py
        ├── documents.py
        ├── health.py
        ├── peers.py
        ├── portfolio.py
        ├── screener.py
        ├── sectors.py
        └── valuation.py
```

---

# Main Application

The central FastAPI application is located at:

```text
src/api/main.py
```

It configures:

- API metadata
- API version
- Application lifespan
- Database startup validation
- CORS middleware
- Request logging middleware
- Root endpoint
- Router registration
- Swagger documentation
- ReDoc documentation
- OpenAPI schema

---

# API Version

```text
1.0.0
```

---

# API Prefix

All application endpoints are registered under:

```text
/api/v1
```

---

# Root Endpoint

## Route

```http
GET /
```

## Purpose

Returns basic API service information.

## Example Response

```json
{
  "name": "Nifty 100 Financial Intelligence API",
  "version": "1.0.0",
  "status": "running",
  "documentation": "/docs",
  "health": "/api/v1/health"
}
```

---

# Health Endpoint

## Route

```http
GET /api/v1/health
```

## Purpose

Returns:

- API status
- API version
- Uptime
- SQLite database path
- Database table count
- Row count for each database table

## Example Response Structure

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 70.434,
  "database": {
    "path": "db/nifty100.db",
    "table_count": 13,
    "db_row_counts": {
      "companies": 92,
      "financial_ratios": 1184
    }
  }
}
```

---

# Readiness Endpoint

## Route

```http
GET /api/v1/health/ready
```

## Purpose

Checks whether:

- The SQLite database is accessible
- Application tables are available
- The API is ready to process requests

## Successful Response

```json
{
  "status": "ready",
  "table_count": 13
}
```

---

# Database Integration

The API dynamically searches for the SQLite database in:

```text
db/nifty100.db
```

and:

```text
data/nifty100.db
```

The first existing database is selected.

The current API successfully connected to:

```text
db/nifty100.db
```

---

# Database Tables Detected

The health endpoint detected 13 application tables:

```text
analysis
balancesheet
cashflow
companies
documents
financial_ratios
market_cap
peer_groups
peer_percentiles
profitandloss
prosandcons
sectors
stock_prices
```

The API calculates row counts dynamically rather than relying on hardcoded table names.

---

# Middleware

## CORS Middleware

CORS is enabled for all origins for internal development usage.

Configured values:

```text
Origins: *
Methods: *
Headers: *
Credentials: Disabled
```

---

## Request Logging Middleware

Every request logs:

- HTTP method
- Request path
- HTTP status
- Processing time

Example:

```text
GET /api/v1/health | 200 | 12.28 ms
```

The response also contains:

```text
X-Process-Time-Ms
```

---

# API Routers

The following router modules were created:

| Router | Planned Responsibility |
|---|---|
| `companies.py` | Company profile and financial history endpoints |
| `screener.py` | Investment screener endpoints |
| `sectors.py` | Sector analytics endpoints |
| `peers.py` | Peer-group comparison endpoints |
| `valuation.py` | Market-cap and valuation endpoints |
| `portfolio.py` | Portfolio statistics endpoints |
| `documents.py` | Annual-report document endpoints |
| `health.py` | API health and readiness endpoints |

The functional endpoints for these routers will be implemented during Days 39 and 40.

---

# Interactive Documentation

## Swagger UI

```text
http://127.0.0.1:8000/docs
```

Swagger UI successfully loaded and displayed:

- Root endpoint
- Health endpoint
- Readiness endpoint
- OpenAPI metadata

---

## ReDoc

```text
http://127.0.0.1:8000/redoc
```

---

## OpenAPI Schema

```text
http://127.0.0.1:8000/openapi.json
```

The OpenAPI schema returned HTTP status `200`.

---

# Server Command

The API can be started using:

```powershell
py -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

---

# Validation Results

| Validation Check | Result |
|---|---|
| FastAPI imports successfully | PASS |
| SQLite connection succeeds | PASS |
| Application startup completes | PASS |
| Root endpoint returns HTTP 200 | PASS |
| Health endpoint returns HTTP 200 | PASS |
| Health status equals `ok` | PASS |
| Database path is reported | PASS |
| Database row counts are returned | PASS |
| API uptime is returned | PASS |
| API version is returned | PASS |
| Request logging works | PASS |
| Swagger UI loads | PASS |
| OpenAPI schema loads | PASS |
| Routers are registered | PASS |

---

# Files Added

```text
src/api/__init__.py
```

```text
src/api/database.py
```

```text
src/api/main.py
```

```text
src/api/routers/__init__.py
```

```text
src/api/routers/companies.py
```

```text
src/api/routers/documents.py
```

```text
src/api/routers/health.py
```

```text
src/api/routers/peers.py
```

```text
src/api/routers/portfolio.py
```

```text
src/api/routers/screener.py
```

```text
src/api/routers/sectors.py
```

```text
src/api/routers/valuation.py
```

```text
docs/sprint_day_038.md
```

---

# Skills Demonstrated

- FastAPI
- REST API Architecture
- SQLite Integration
- Middleware
- CORS
- Request Logging
- API Versioning
- Health Checks
- Readiness Checks
- OpenAPI
- Swagger UI
- Modular Router Architecture
- Python Type Hints
- Application Lifespan Management

---

# Result

Successfully created and validated the FastAPI server scaffold for the Nifty 100 Financial Intelligence Platform.

The API starts without errors, connects to the SQLite database, exposes health diagnostics, logs incoming requests, and provides interactive OpenAPI documentation.

---

# Day 38 Status

```text
COMPLETE
```