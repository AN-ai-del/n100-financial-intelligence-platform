"""Portfolio analytics API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)