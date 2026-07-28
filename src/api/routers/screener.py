"""Financial screener API router."""

from fastapi import APIRouter


router = APIRouter(
    prefix="/screener",
    tags=["Screener"],
)