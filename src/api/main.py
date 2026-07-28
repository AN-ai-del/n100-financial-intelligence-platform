"""FastAPI application for the Nifty 100 intelligence platform."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.database import (
    DB_PATH,
    create_connection,
)
from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)


API_VERSION = "1.0.0"
API_PREFIX = "/api/v1"

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "nifty100_api"
)


def get_db_connection():
    """Return a configured SQLite database connection."""

    return create_connection()


def validate_database_connection() -> None:
    """Verify that the SQLite database can be opened."""

    with get_db_connection() as connection:
        connection.execute(
            "SELECT 1"
        ).fetchone()


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Run API startup and shutdown tasks."""

    app.state.startup_time = (
        time.perf_counter()
    )

    validate_database_connection()

    logger.info(
        "Nifty 100 API started"
    )

    logger.info(
        "Database path: %s",
        DB_PATH,
    )

    yield

    logger.info(
        "Nifty 100 API stopped"
    )


app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description=(
        "REST API for company fundamentals, "
        "financial screening, sector analytics, "
        "peer comparison, valuation and "
        "portfolio intelligence."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    """Log the method, path, status and response time."""

    started_at = time.perf_counter()

    try:
        response = await call_next(
            request
        )

    except Exception:
        elapsed_ms = (
            time.perf_counter()
            - started_at
        ) * 1000

        logger.exception(
            "%s %s | failed | %.2f ms",
            request.method,
            request.url.path,
            elapsed_ms,
        )

        raise

    elapsed_ms = (
        time.perf_counter()
        - started_at
    ) * 1000

    logger.info(
        "%s %s | %s | %.2f ms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )

    response.headers[
        "X-Process-Time-Ms"
    ] = f"{elapsed_ms:.2f}"

    return response


@app.get(
    "/",
    tags=["Root"],
    summary="API landing endpoint",
)
def root() -> dict[str, str]:
    """Return basic service information."""

    return {
        "name":
            "Nifty 100 Financial Intelligence API",

        "version":
            API_VERSION,

        "status":
            "running",

        "documentation":
            "/docs",

        "health":
            f"{API_PREFIX}/health",
    }


app.include_router(
    health.router,
    prefix=API_PREFIX,
)

app.include_router(
    companies.router,
    prefix=API_PREFIX,
)

app.include_router(
    screener.router,
    prefix=API_PREFIX,
)

app.include_router(
    sectors.router,
    prefix=API_PREFIX,
)

app.include_router(
    peers.router,
    prefix=API_PREFIX,
)

app.include_router(
    valuation.router,
    prefix=API_PREFIX,
)

app.include_router(
    portfolio.router,
    prefix=API_PREFIX,
)

app.include_router(
    documents.router,
    prefix=API_PREFIX,
)