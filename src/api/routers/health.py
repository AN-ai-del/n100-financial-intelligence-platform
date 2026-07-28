"""Health-check endpoint for the Nifty 100 API."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from src.api.database import (
    DB_PATH,
    get_database_row_counts,
)


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    summary="Check API and database health",
    response_description="API status and SQLite table counts",
)
def health_check(
    request: Request,
) -> dict[str, Any]:
    """Return service status, database counts, uptime and version."""

    try:
        row_counts = (
            get_database_row_counts()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message":
                    "Database health check failed.",

                "error":
                    str(exc),
            },
        ) from exc

    startup_time = float(
        request.app.state.startup_time
    )

    uptime_seconds = round(
        time.perf_counter()
        - startup_time,
        3,
    )

    version = str(
        request.app.version
    )

    return {
        "status":
            "ok",

        "version":
            version,

        "uptime_seconds":
            uptime_seconds,

        "database":
            {
                "path":
                    str(DB_PATH),

                "table_count":
                    len(row_counts),

                "db_row_counts":
                    row_counts,
            },
    }


@router.get(
    "/ready",
    summary="Check whether the API is ready",
)
def readiness_check() -> JSONResponse:
    """Return readiness status after verifying database access."""

    try:
        row_counts = (
            get_database_row_counts()
        )

    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status":
                    "not_ready",

                "error":
                    str(exc),
            },
        )

    if not row_counts:
        return JSONResponse(
            status_code=503,
            content={
                "status":
                    "not_ready",

                "error":
                    "No application tables were found.",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status":
                "ready",

            "table_count":
                len(row_counts),
        },
    )