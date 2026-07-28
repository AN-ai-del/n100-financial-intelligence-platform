"""Company valuation API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/market-cap",
    tags=["Valuation"],
)